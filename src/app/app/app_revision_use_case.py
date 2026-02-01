"""App 수정 Use Case"""

from typing import Optional, Dict

from fastapi import Depends

from src.api.v1.app.schemas.request import AppRevisionRequest
from src.api.v1.app.schemas.response import (
    AppRevisionResponse,
    ContainerResourceInfo,
    ContainerResourcesInfo,
)
from src.app.base_use_case import BaseUseCase
from src.core.exceptions import BadRequestException
from src.dependencies.kubernetes import get_deployment_manager


class AppRevisionUseCase(BaseUseCase):
    """App(Deployment) 리소스 수정 Use Case"""

    def __init__(
            self,
            deployment_manager=Depends(get_deployment_manager),
    ):
        self.deployment_manager = deployment_manager

    async def __call__(
            self,
            name: str,
            namespace: str,
            payload: AppRevisionRequest,
            user_id: str
    ) -> AppRevisionResponse:
        """App(Deployment) 리소스 수정"""

        # 기존 Deployment 조회
        existing = await self.deployment_manager.get_deployment(name, namespace)
        if not existing:
            raise BadRequestException(detail=f"Deployment '{name}' not found in namespace '{namespace}'")

        # 컨테이너 이름 결정
        containers = existing.spec.template.spec.containers
        if not containers:
            raise BadRequestException(detail="No containers found in deployment")

        container_name = payload.container_name or containers[0].name

        # 리소스 업데이트
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

        # 리소스 업데이트 실행
        if requests_dict or limits_dict:
            await self.deployment_manager.update_container_resources(
                name=name,
                namespace=namespace,
                container_name=container_name,
                requests=requests_dict,
                limits=limits_dict,
            )

        # 레플리카 업데이트
        if payload.replicas is not None:
            await self.deployment_manager.update_replicas(
                name=name,
                namespace=namespace,
                replicas=payload.replicas,
            )

        # 최신 상태 조회
        updated = await self.deployment_manager.get_deployment(name, namespace)

        # 수정된 컨테이너 리소스 정보 추출
        updated_container = None
        for c in updated.spec.template.spec.containers:
            if c.name == container_name:
                updated_container = c
                break

        resources_info = ContainerResourcesInfo()
        if updated_container and updated_container.resources:
            res = updated_container.resources
            if res.requests:
                resources_info.requests = ContainerResourceInfo(
                    cpu=res.requests.get("cpu"),
                    memory=res.requests.get("memory"),
                )
            if res.limits:
                resources_info.limits = ContainerResourceInfo(
                    cpu=res.limits.get("cpu"),
                    memory=res.limits.get("memory"),
                )

        return AppRevisionResponse(
            name=updated.metadata.name,
            namespace=updated.metadata.namespace,
            replicas=updated.spec.replicas,
            container_name=container_name,
            resources=resources_info,
        )
