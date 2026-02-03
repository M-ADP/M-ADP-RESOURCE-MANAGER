"""App 생성 Use Case"""

from typing import List

from fastapi import Depends

from src.api.v1.app.schemas.request import AppCreateRequest, ContainerSpec
from src.api.v1.app.schemas.response import (
    AppCreateResponse,
    ContainerInfo,
    DeploymentStatusInfo,
    PvcInfo,
)
from src.app.base_use_case import BaseUseCase
from src.common.const import DefaultLabel
from src.core.kubernetes.deployment import Deployment, Container, Volume
from src.core.kubernetes.persistent_volume_claim import PersistentVolumeClaim
from src.core.kubernetes.service_account import ServiceAccount
from src.dependencies.kubernetes import get_deployment_repository, get_pvc_repository, get_service_account_repository


class AppCreateUseCase(BaseUseCase):
    """App(Deployment) 생성 Use Case"""

    def __init__(
            self,
            deployment_repository=Depends(get_deployment_repository),
            pvc_repository=Depends(get_pvc_repository),
            service_account_repository=Depends(get_service_account_repository),
    ):
        self.deployment_repository = deployment_repository
        self.pvc_repository = pvc_repository
        self.service_account_repository = service_account_repository

    async def __call__(
            self,
            payload: AppCreateRequest,
            user_id: str
    ) -> AppCreateResponse:
        """App(Deployment) 생성"""

        # 1. ServiceAccount 생성
        sa_name = f"{payload.name}-sa"
        sa_domain = ServiceAccount(
            name=sa_name,
            namespace=payload.namespace,
            labels={
                "app": payload.name,
                "owner": user_id,
                **DefaultLabel.MANAGED_BY_LABEL,
            }
        )
        await self.service_account_repository.save(sa_domain)

        # 2. PVC 생성 및 정보 수집
        pvc_infos: List[PvcInfo] = []
        volumes: List[Volume] = []

        for spec in payload.containers:
            if spec.disk:
                pvc_name = f"{payload.name}-{spec.name}-pvc"

                # PVC 도메인 객체 생성
                pvc_domain = PersistentVolumeClaim(
                    name=pvc_name,
                    namespace=payload.namespace,
                    storage=spec.disk.size,
                    storage_class_name=spec.disk.storage_class,
                    access_modes=["ReadWriteOnce"],
                    labels={
                        "app": payload.name,
                        "container": spec.name,
                        "owner": user_id,
                        **DefaultLabel.MANAGED_BY_LABEL,
                    },
                )

                # Repository를 통해 PVC 저장
                saved_pvc = await self.pvc_repository.save(pvc_domain)

                # Volume 정의 추가
                volumes.append(
                    Volume(
                        name=f"{spec.name}-volume",
                        pvc_name=pvc_name
                    )
                )

                # PVC 정보 수집
                pvc_infos.append(PvcInfo(
                    name=pvc_name,
                    size=spec.disk.size,
                    mount_path=spec.disk.mount_path,
                    storage_class=spec.disk.storage_class,
                    phase=saved_pvc.phase,
                ))

        # ContainerSpec -> Container 도메인 객체 변환
        containers = self._build_containers(payload.containers)

        # 레이블 설정 (기본 레이블 + 사용자 레이블)
        labels = {
            "app": payload.name,
            "owner": user_id,
            **DefaultLabel.MANAGED_BY_LABEL,
        }
        if payload.labels:
            labels.update(payload.labels)

        # Deployment 도메인 객체 생성
        deployment_domain = Deployment(
            name=payload.name,
            namespace=payload.namespace,
            replicas=payload.replicas,
            containers=containers,
            volumes=volumes,
            labels=labels,
            annotations=payload.annotations or {},
            service_account_name=sa_name,
        )

        # Repository를 통해 Deployment 저장
        saved_deployment = await self.deployment_repository.save(deployment_domain)

        # 응답 생성
        container_infos = [
            ContainerInfo(
                name=c.name,
                image=c.image
            )
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
        """ContainerSpec 리스트를 Container 도메인 객체 리스트로 변환"""
        containers = []

        for spec in container_specs:
            # 포트 설정
            ports = []
            if spec.ports and len(spec.ports) > 0:
                ports = [{"container_port": port} for port in spec.ports]

            # 리소스 설정
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

            # 환경 변수 설정
            env = []
            if spec.env:
                env = [{"name": key, "value": value} for key, value in spec.env.items()]

            # 볼륨 마운트 설정
            volume_mounts = []
            if spec.disk:
                volume_mounts = [
                    {
                        "name": f"{spec.name}-volume",
                        "mount_path": spec.disk.mount_path,
                    }
                ]

            container = Container(
                name=spec.name,
                image=spec.image,
                ports=ports,
                resources=resources,
                env=env,
                command=spec.command,
                args=spec.args,
                volume_mounts=volume_mounts,
            )
            containers.append(container)

        return containers
