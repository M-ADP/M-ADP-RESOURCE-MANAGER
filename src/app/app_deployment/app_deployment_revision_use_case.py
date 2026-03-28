"""App Deployment 수정 Use Case"""

from typing import Optional, Dict

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.request import AppRevisionRequest
from src.api.v1.app.schemas.response import (
    AppRevisionResponse,
    ContainerResourceInfo,
    ContainerResourcesInfo,
    PvcInfo,
)
from src.app.base_use_case import BaseUseCase
from src.app.app_deployment.exceptions import (
    DeploymentNotFoundException,
    ContainerNotFoundException,
    PvcNotFoundException,
    DiskReductionNotAllowedException,
)
from src.common.util import UnitConverter, NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentRevisionUseCase(BaseUseCase):
    """App Deployment 리소스 수정 Use Case"""

    def __init__(
            self,
            app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
            self,
            app_name: str,
            project_id: str,
            payload: AppRevisionRequest,
    ) -> AppRevisionResponse:
        """App(Deployment) 리소스 수정"""

        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        if not deployment.containers:
            raise ContainerNotFoundException(deployment_name=app_name)

        container_name = payload.container_name or deployment.containers[0].name

        # 컨테이너 리소스 조정
        requests_dict: Optional[Dict[str, str]] = None
        limits_dict: Optional[Dict[str, str]] = None

        if payload.requests:
            requests_dict = {}
            if payload.requests.cpu:
                requests_dict["cpu"] = payload.requests.cpu
            if payload.requests.memory:
                requests_dict["memory"] = payload.requests.memory

        if payload.limits:
            limits_dict = {}
            if payload.limits.cpu:
                limits_dict["cpu"] = payload.limits.cpu
            if payload.limits.memory:
                limits_dict["memory"] = payload.limits.memory

        if requests_dict or limits_dict:
            deployment = await self.app_deployment_repo.resize_container(
                deployment=deployment,
                container_name=container_name,
                requests=requests_dict,
                limits=limits_dict,
            )

        # 스토리지 확장
        pvc_info: Optional[PvcInfo] = None
        if payload.disk:
            pvc_name = f"{app_name}-{container_name}-pvc"
            existing_pvc = await self.app_deployment_repo.find_storage(pvc_name, namespace)

            if not existing_pvc:
                raise PvcNotFoundException(name=pvc_name, namespace=namespace)

            current_bytes = UnitConverter.parse_storage_to_bytes(existing_pvc.storage)
            new_bytes = UnitConverter.parse_storage_to_bytes(payload.disk.size)

            if new_bytes < current_bytes:
                raise DiskReductionNotAllowedException(
                    current=existing_pvc.storage,
                    requested=payload.disk.size,
                )

            if new_bytes > current_bytes:
                updated_pvc = await self.app_deployment_repo.expand_storage(
                    pvc=existing_pvc,
                    new_size=payload.disk.size,
                )

                mount_path = "/data"
                for c in deployment.containers:
                    if c.name == container_name and c.volume_mounts:
                        for vm in c.volume_mounts:
                            if vm.get("name") == f"{container_name}-volume":
                                mount_path = vm.get("mount_path", "/data")
                                break

                pvc_info = PvcInfo(
                    name=pvc_name,
                    size=payload.disk.size,
                    mount_path=mount_path,
                    storage_class=updated_pvc.storage_class_name,
                    phase=updated_pvc.phase,
                )

        # 레플리카 수 조정
        if payload.replicas is not None:
            deployment = await self.app_deployment_repo.scale(deployment, payload.replicas)

        updated_container = None
        for c in deployment.containers:
            if c.name == container_name:
                updated_container = c
                break

        resources_info = ContainerResourcesInfo()
        if updated_container and updated_container.resources:
            res = updated_container.resources
            if res.get("requests"):
                resources_info.requests = ContainerResourceInfo(
                    cpu=res["requests"].get("cpu"),
                    memory=res["requests"].get("memory"),
                )
            if res.get("limits"):
                resources_info.limits = ContainerResourceInfo(
                    cpu=res["limits"].get("cpu"),
                    memory=res["limits"].get("memory"),
                )

        return AppRevisionResponse(
            name=deployment.name,
            namespace=deployment.namespace,
            replicas=deployment.replicas,
            container_name=container_name,
            resources=resources_info,
            pvc=pvc_info,
        )
