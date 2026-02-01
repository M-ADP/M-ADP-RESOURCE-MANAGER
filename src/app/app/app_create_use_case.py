"""App 생성 Use Case"""

from typing import List, Tuple

from fastapi import Depends
from kubernetes_asyncio.client import (
    V1Container,
    V1ContainerPort,
    V1ResourceRequirements,
    V1EnvVar,
    V1VolumeMount,
    V1Volume,
    V1PersistentVolumeClaimVolumeSource,
)

from src.api.v1.app.schemas.request import AppCreateRequest, ContainerSpec
from src.api.v1.app.schemas.response import (
    AppCreateResponse,
    ContainerInfo,
    DeploymentStatusInfo,
    PvcInfo,
)
from src.app.base_use_case import BaseUseCase
from src.dependencies.kubernetes import get_deployment_manager, get_pvc_manager


class AppCreateUseCase(BaseUseCase):
    """App(Deployment) 생성 Use Case"""

    def __init__(
            self,
            deployment_manager=Depends(get_deployment_manager),
            pvc_manager=Depends(get_pvc_manager),
    ):
        self.deployment_manager = deployment_manager
        self.pvc_manager = pvc_manager

    async def __call__(
            self,
            payload: AppCreateRequest,
            user_id: str
    ) -> AppCreateResponse:
        """App(Deployment) 생성"""

        # PVC 생성 및 정보 수집
        pvc_infos: List[PvcInfo] = []
        volumes: List[V1Volume] = []

        for spec in payload.containers:
            if spec.disk:
                pvc_name = f"{payload.name}-{spec.name}-pvc"

                # PVC 생성
                pvc = await self.pvc_manager.create_pvc(
                    name=pvc_name,
                    namespace=payload.namespace,
                    storage_size=spec.disk.size,
                    storage_class_name=spec.disk.storage_class,
                    access_modes=["ReadWriteOnce"],
                    labels={
                        "app": payload.name,
                        "container": spec.name,
                        "managed-by": "madp-rms",
                        "owner": user_id,
                    },
                )

                # Volume 정의 추가
                volumes.append(
                    V1Volume(
                        name=f"{spec.name}-volume",
                        persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                            claim_name=pvc_name
                        )
                    )
                )

                # PVC 정보 수집
                pvc_infos.append(PvcInfo(
                    name=pvc_name,
                    size=spec.disk.size,
                    mount_path=spec.disk.mount_path,
                    storage_class=spec.disk.storage_class,
                    phase=pvc.status.phase if pvc.status else None,
                ))

        # ContainerSpec -> V1Container 변환 (volumeMounts 포함)
        containers = self._build_containers(payload.containers)

        # 레이블 설정 (기본 레이블 + 사용자 레이블)
        labels = {
            "app": payload.name,
            "managed-by": "madp-rms",
            "owner": user_id,
        }
        if payload.labels:
            labels.update(payload.labels)

        # Deployment 생성
        deployment = await self.deployment_manager.create_deployment(
            name=payload.name,
            namespace=payload.namespace,
            containers=containers,
            replicas=payload.replicas,
            labels=labels,
            annotations=payload.annotations,
            volumes=volumes if volumes else None,
        )

        # 응답 생성
        container_infos = [
            ContainerInfo(
                name=c.name,
                image=c.image
            )
            for c in deployment.spec.template.spec.containers
        ]

        status_info = None
        if deployment.status:
            status_info = DeploymentStatusInfo(
                replicas=deployment.status.replicas,
                ready_replicas=deployment.status.ready_replicas,
                available_replicas=deployment.status.available_replicas,
                updated_replicas=deployment.status.updated_replicas,
            )

        return AppCreateResponse(
            name=deployment.metadata.name,
            namespace=deployment.metadata.namespace,
            replicas=deployment.spec.replicas,
            containers=container_infos,
            pvcs=pvc_infos,
            labels=deployment.metadata.labels,
            status=status_info,
        )

    def _build_containers(self, container_specs: List[ContainerSpec]) -> List[V1Container]:
        """ContainerSpec 리스트를 V1Container 리스트로 변환"""
        containers = []

        for spec in container_specs:
            # 포트 설정 (빈 리스트나 None이면 ports를 None으로 설정)
            ports = None
            if spec.ports and len(spec.ports) > 0:
                ports = [
                    V1ContainerPort(container_port=port)
                    for port in spec.ports
                ]

            # 리소스 설정
            resources = V1ResourceRequirements(
                requests={
                    "cpu": spec.resources.requests.cpu,
                    "memory": spec.resources.requests.memory,
                },
                limits={
                    "cpu": spec.resources.limits.cpu,
                    "memory": spec.resources.limits.memory,
                },
            )

            # 환경 변수 설정
            env = None
            if spec.env:
                env = [
                    V1EnvVar(name=key, value=value)
                    for key, value in spec.env.items()
                ]

            # 볼륨 마운트 설정
            volume_mounts = None
            if spec.disk:
                volume_mounts = [
                    V1VolumeMount(
                        name=f"{spec.name}-volume",
                        mount_path=spec.disk.mount_path,
                    )
                ]

            container = V1Container(
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
