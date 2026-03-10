"""App Deployment 생성 Use Case"""

from typing import List

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.request import AppCreateRequest, ContainerSpec
from src.api.v1.app.schemas.response import (
    AppCreateResponse,
    ContainerInfo,
    DeploymentStatusInfo,
    PvcInfo,
)
from src.app.base_use_case import BaseUseCase
from src.app.project.exceptions import ProjectNotFoundException
from src.common.config.harbor import HarborConfig
from src.common.const import DefaultLabel
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.core.kubernetes.deployment import Deployment, Container, Volume
from src.core.kubernetes.persistent_volume_claim import PersistentVolumeClaim
from src.core.kubernetes.service_account import ServiceAccount
from src.dependencies.kubernetes import get_app_deployment_repository
from src.infra.kubernetes.managers.namespace.exceptions import NamespaceNotFoundException


class AppDeploymentCreateUseCase(BaseUseCase):
    """App Deployment 생성 Use Case"""

    def __init__(
            self,
            app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo
        self._harbor = HarborConfig()

    async def __call__(
            self,
            project_id: str,
            payload: AppCreateRequest,
    ) -> AppCreateResponse:
        """App(Deployment) 생성"""

        namespace = ProjectId(project_id).namespace

        # K8s 이름 규칙(RFC 1123): 한글 로마자 변환 + 소문자 + 유효하지 않은 문자 제거
        k8s_name = NameConverter.to_k8s_name(payload.name)

        # naming convention은 Deployment 도메인 객체에서 결정되므로
        # 임시 객체로 이름을 도출한다
        _name_ref = Deployment(name=k8s_name, namespace=namespace)

        # 1. ID(ServiceAccount) 바인딩
        sa = ServiceAccount(
            name=_name_ref.sa_name,
            namespace=namespace,
            labels={
                "app_deployment": payload.name,
                **DefaultLabel.MANAGED_BY_LABEL,
            },
            image_pull_secrets=[self._harbor.pull_secret_name],
        )
        try:
            await self.app_deployment_repo.bind_identity(sa)
        except NamespaceNotFoundException as exc:
            raise ProjectNotFoundException() from exc

        # 2. 스토리지 프로비저닝
        pvc_infos: List[PvcInfo] = []
        volumes: List[Volume] = []

        for spec in payload.containers:
            if spec.disk:
                pvc_name = f"{k8s_name}-{spec.name}-pvc"
                access_modes = ["ReadWriteOnce"]

                pvc = PersistentVolumeClaim(
                    name=pvc_name,
                    namespace=namespace,
                    storage=spec.disk.size,
                    storage_class_name=spec.disk.storage_class,
                    access_modes=access_modes,
                    labels={
                        "app_deployment": payload.name,
                        "container": spec.name,
                        **DefaultLabel.MANAGED_BY_LABEL,
                    },
                )

                saved_pvc = await self.app_deployment_repo.provision_storage(pvc)

                volumes.append(Volume(name=f"{spec.name}-volume", pvc_name=pvc_name))
                pvc_infos.append(PvcInfo(
                    name=pvc_name,
                    size=spec.disk.size,
                    mount_path=spec.disk.mount_path,
                    storage_class=spec.disk.storage_class,
                    phase=saved_pvc.phase,
                ))

        # 3. Deployment 배포
        labels = {
            "app_deployment": k8s_name,
            "x-project-id": namespace,
            "x-app-deployment-id": k8s_name,
            **DefaultLabel.MANAGED_BY_LABEL,
        }

        if payload.labels:
            labels.update(payload.labels)

        deployment = Deployment(
            name=k8s_name,
            namespace=namespace,
            replicas=payload.replicas,
            containers=self._build_containers(payload.containers),
            volumes=volumes,
            labels=labels,
            annotations=payload.annotations or {},
            service_account_name=_name_ref.sa_name,
            image_pull_secrets=[self._harbor.pull_secret_name],
        )

        saved_deployment = await self.app_deployment_repo.deploy(deployment)

        container_infos = [
            ContainerInfo(name=c.name, image=c.image)
            for c in saved_deployment.containers
        ]

        status_info = None
        if saved_deployment.status:
            status_info = DeploymentStatusInfo(
                replicas=saved_deployment.status.replicas,
                ready_replicas=saved_deployment.status.ready_replicas,
                available_replicas=saved_deployment.status.available_replicas,
                updated_replicas=saved_deployment.status.updated_replicas,
            )

        return AppCreateResponse(
            name=saved_deployment.name,
            namespace=saved_deployment.namespace,
            replicas=saved_deployment.replicas,
            containers=container_infos,
            pvcs=pvc_infos,
            labels=saved_deployment.labels,
            status=status_info,
        )

    def _build_containers(self, container_specs: List[ContainerSpec]) -> List[Container]:
        containers = []
        for spec in container_specs:
            ports = []
            if spec.ports:
                ports = [{"container_port": port} for port in spec.ports]

            resources = {
                "requests": {
                    "cpu": spec.resources.requests.cpu,
                    "memory": spec.resources.requests.memory,
                },
                "limits": {
                    "cpu": spec.resources.limits.cpu,
                    "memory": spec.resources.limits.memory,
                },
            }

            env = []
            if spec.env:
                env = [{"name": key, "value": value} for key, value in spec.env.items()]

            volume_mounts = []
            if spec.disk:
                volume_mounts = [{"name": f"{spec.name}-volume", "mount_path": spec.disk.mount_path}]

            containers.append(Container(
                name=spec.name,
                image=spec.image,
                ports=ports,
                resources=resources,
                env=env,
                command=spec.command,
                args=spec.args,
                volume_mounts=volume_mounts,
            ))
        return containers
