"""App Deployment 생성 Use Case"""

from typing import List

from typing import List

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.request import AppCreateRequest
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
from src.api.v1.app.schemas.request import MIN_CPU_REQUEST, MIN_MEMORY_REQUEST
from src.core.app_deployment import AppContainer, AppContainerDisk, AppDeployment, AppDeploymentRepository
from src.core.kubernetes.deployment import Container, Deployment, Volume
from src.core.kubernetes.persistent_volume_claim import PersistentVolumeClaim
from src.core.kubernetes.service_account import ServiceAccount
from src.dependencies.kubernetes import get_app_deployment_repository, get_service_manager
from src.infra.kubernetes.managers.namespace.exceptions import NamespaceNotFoundException
from src.infra.kubernetes.managers.service import ServiceManager


class AppDeploymentCreateUseCase(BaseUseCase):
    """App Deployment 생성 Use Case"""

    def __init__(
            self,
            app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
            service_manager: ServiceManager = Depends(get_service_manager),
    ):
        self.app_deployment_repo = app_deployment_repo
        self.service_manager = service_manager
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

        # 2. AppDeployment 도메인 객체 생성 (Harbor URL 포함)
        labels = {
            "app_deployment": k8s_name,
            "x-project-id": namespace,
            "x-app-deployment-id": payload.deployment_id,
            **DefaultLabel.MANAGED_BY_LABEL,
        }
        if payload.labels:
            labels.update(payload.labels)

        app_deployment = self._build_app_deployment(
            name=k8s_name,
            namespace=namespace,
            payload=payload,
            labels=labels,
        )

        # 3. 스토리지 프로비저닝
        pvc_infos: List[PvcInfo] = []
        volumes: List[Volume] = []

        for container in app_deployment.containers:
            if container.disk:
                pvc_name = f"{k8s_name}-{container.name}-pvc"

                pvc = PersistentVolumeClaim(
                    name=pvc_name,
                    namespace=namespace,
                    storage=container.disk.size,
                    storage_class_name=container.disk.storage_class,
                    access_modes=["ReadWriteOnce"],
                    labels={
                        "app_deployment": payload.name,
                        "container": container.name,
                        **DefaultLabel.MANAGED_BY_LABEL,
                    },
                )

                saved_pvc = await self.app_deployment_repo.provision_storage(pvc)

                volumes.append(Volume(name=f"{container.name}-volume", pvc_name=pvc_name))
                pvc_infos.append(PvcInfo(
                    name=pvc_name,
                    size=container.disk.size,
                    mount_path=container.disk.mount_path,
                    storage_class=container.disk.storage_class,
                    phase=saved_pvc.phase,
                ))

        # 4. Deployment 배포
        deployment = Deployment(
            name=app_deployment.name,
            namespace=app_deployment.namespace,
            replicas=app_deployment.replicas,
            containers=self._build_k8s_containers(app_deployment.containers),
            volumes=volumes,
            labels=app_deployment.labels,
            annotations=app_deployment.annotations,
            service_account_name=_name_ref.sa_name,
            image_pull_secrets=[self._harbor.pull_secret_name],
        )

        saved_deployment = await self.app_deployment_repo.deploy(deployment)

        # 5. Service(ClusterIP) 생성 — 포트 없으면 기본값 80 사용
        all_ports = [
            port
            for spec in payload.containers
            for port in (spec.ports or [])
        ] or [80]
        await self.service_manager.create_service(
            name=f"{k8s_name}-svc",
            namespace=namespace,
            selector={"app_deployment": k8s_name},
            ports=[
                {"port": p, "target_port": p, "protocol": "TCP", "name": f"port-{p}"}
                for p in all_ports
            ],
            service_type="ClusterIP",
            labels={
                "app_deployment": k8s_name,
                **DefaultLabel.MANAGED_BY_LABEL,
            },
        )

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

    def _build_app_deployment(
            self,
            name: str,
            namespace: str,
            payload: AppCreateRequest,
            labels: dict,
    ) -> AppDeployment:
        """API 요청을 AppDeployment 도메인 객체로 변환.

        Harbor URL을 이미지 경로 앞에 붙인다.
        """
        containers = []
        for spec in payload.containers:
            disk = None
            if spec.disk:
                disk = AppContainerDisk(
                    size=spec.disk.size,
                    mount_path=spec.disk.mount_path,
                    storage_class=spec.disk.storage_class,
                )
            containers.append(AppContainer(
                name=spec.name,
                image=spec.image,
                harbor_url=self._harbor.url,
                ports=spec.ports or [],
                resources={
                    "requests": {
                        "cpu": MIN_CPU_REQUEST,
                        "memory": MIN_MEMORY_REQUEST,
                    },
                    "limits": {
                        "cpu": spec.resources.limits.cpu,
                        "memory": spec.resources.limits.memory,
                    },
                },
                env=spec.env or {},
                command=spec.command,
                args=spec.args,
                disk=disk,
            ))
        return AppDeployment(
            name=name,
            namespace=namespace,
            containers=containers,
            replicas=payload.replicas,
            labels=labels,
            annotations=payload.annotations or {},
        )

    def _build_k8s_containers(self, containers: List[AppContainer]) -> List[Container]:
        """AppContainer 목록을 K8s Container 도메인 객체로 변환"""
        k8s_containers = []
        for c in containers:
            ports = [{"container_port": port} for port in c.ports]
            env = [{"name": key, "value": value} for key, value in c.env.items()]
            volume_mounts = []
            if c.disk:
                volume_mounts = [{"name": f"{c.name}-volume", "mount_path": c.disk.mount_path}]

            k8s_containers.append(Container(
                name=c.name,
                image=c.full_image,
                ports=ports,
                resources=c.resources,
                env=env,
                command=c.command,
                args=c.args,
                volume_mounts=volume_mounts,
            ))
        return k8s_containers
