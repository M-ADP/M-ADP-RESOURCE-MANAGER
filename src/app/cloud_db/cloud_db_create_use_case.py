"""Cloud DB 생성 Use Case"""

from typing import List

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.cloud_db.schemas.request import (
    CloudDBCreateRequest,
    CloudDBContainerSpec,
    CLOUD_DB_IMAGES,
    CLOUD_DB_DEFAULT_PORTS,
    CLOUD_DB_MOUNT_PATHS,
)
from src.api.v1.cloud_db.schemas.response import (
    CloudDbCreateResponse,
    ContainerInfo,
    DeploymentStatusInfo,
    PvcInfo,
)
from src.app.base_use_case import BaseUseCase
from src.app.project.exceptions import ProjectNotFoundException
from src.common.config.harbor import HarborConfig
from src.common.const import DefaultLabel
from src.common.util import NameConverter
from src.core.cloud_db import CloudDb, CloudDbContainer, CloudDbContainerDisk, CloudDbRepository
from src.core.kubernetes.deployment import Container, Deployment, Volume
from src.core.kubernetes.persistent_volume_claim import PersistentVolumeClaim
from src.core.kubernetes.service_account import ServiceAccount
from src.dependencies.kubernetes import get_cloud_db_repository, get_service_manager
from src.infra.kubernetes.managers.namespace.exceptions import NamespaceNotFoundException
from src.infra.kubernetes.managers.service import ServiceManager


class CloudDbCreateUseCase(BaseUseCase):
    """Cloud DB 생성 Use Case"""

    def __init__(
            self,
            cloud_db_repo: CloudDbRepository = Depends(get_cloud_db_repository),
            service_manager: ServiceManager = Depends(get_service_manager),
    ):
        self.cloud_db_repo = cloud_db_repo
        self.service_manager = service_manager
        self._harbor = HarborConfig()

    async def __call__(
            self,
            project_id: str,
            payload: CloudDBCreateRequest,
    ) -> CloudDbCreateResponse:
        """Cloud DB(StatefulSet) 생성"""

        namespace = ProjectId(project_id).namespace
        k8s_name = NameConverter.to_k8s_name(payload.name, prefix="db-")

        _name_ref = Deployment(name=k8s_name, namespace=namespace)

        # 1. ID(ServiceAccount) 바인딩
        sa = ServiceAccount(
            name=_name_ref.sa_name,
            namespace=namespace,
            labels={
                "cloud_db": payload.name,
                **DefaultLabel.MANAGED_BY_LABEL,
            },
            image_pull_secrets=[self._harbor.pull_secret_name],
        )
        try:
            await self.cloud_db_repo.bind_identity(sa)
        except NamespaceNotFoundException as exc:
            raise ProjectNotFoundException() from exc

        # 2. CloudDb 도메인 객체 생성
        labels = {
            "cloud_db": k8s_name,
            "x-project-id": namespace,
            "x-cloud-db-id": k8s_name,
            **DefaultLabel.MANAGED_BY_LABEL,
        }
        if payload.labels:
            labels.update(payload.labels)

        cloud_db = self._build_cloud_db(
            name=k8s_name,
            namespace=namespace,
            payload=payload,
            labels=labels,
        )

        # 3. 스토리지 프로비저닝
        pvc_infos: List[PvcInfo] = []
        volumes: List[Volume] = []

        for container in cloud_db.containers:
            if container.disk:
                pvc_name = f"{k8s_name}-{container.name}-pvc"

                pvc = PersistentVolumeClaim(
                    name=pvc_name,
                    namespace=namespace,
                    storage=container.disk.size,
                    storage_class_name=container.disk.storage_class,
                    access_modes=["ReadWriteOnce"],
                    labels={
                        "cloud_db": payload.name,
                        "container": container.name,
                        **DefaultLabel.MANAGED_BY_LABEL,
                    },
                )

                saved_pvc = await self.cloud_db_repo.provision_storage(pvc)

                volumes.append(Volume(name=f"{container.name}-volume", pvc_name=pvc_name))
                pvc_infos.append(PvcInfo(
                    name=pvc_name,
                    size=container.disk.size,
                    mount_path=container.disk.mount_path,
                    storage_class=container.disk.storage_class,
                    phase=saved_pvc.phase,
                ))

        # 4. StatefulSet 배포
        deployment = Deployment(
            name=cloud_db.name,
            namespace=cloud_db.namespace,
            replicas=cloud_db.replicas,
            containers=self._build_k8s_containers(cloud_db.containers),
            volumes=volumes,
            labels=cloud_db.labels,
            annotations=cloud_db.annotations,
            service_account_name=_name_ref.sa_name,
            image_pull_secrets=[self._harbor.pull_secret_name],
            selector_labels={"cloud_db": k8s_name},
        )

        saved_deployment = await self.cloud_db_repo.deploy(deployment)

        # 5. Headless Service 생성 (StatefulSet governing service)
        headless_service_name = f"{k8s_name}-headless"
        default_ports = CLOUD_DB_DEFAULT_PORTS[payload.type]
        all_ports = [
            port
            for spec in payload.containers
            for port in (spec.ports or [])
        ] or default_ports
        await self.service_manager.create_service(
            name=headless_service_name,
            namespace=namespace,
            selector={"cloud_db": k8s_name},
            ports=[
                {"port": p, "target_port": p, "protocol": "TCP", "name": f"port-{p}"}
                for p in all_ports
            ],
            service_type="ClusterIP",
            cluster_ip="None",
            labels={
                "cloud_db": k8s_name,
                **DefaultLabel.MANAGED_BY_LABEL,
            },
        )

        # 6. ClusterIP Service 생성 (일반 접근용)
        await self.service_manager.create_service(
            name=f"{k8s_name}-svc",
            namespace=namespace,
            selector={"cloud_db": k8s_name},
            ports=[
                {"port": p, "target_port": p, "protocol": "TCP", "name": f"port-{p}"}
                for p in all_ports
            ],
            service_type="ClusterIP",
            labels={
                "cloud_db": k8s_name,
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

        return CloudDbCreateResponse(
            name=saved_deployment.name,
            namespace=saved_deployment.namespace,
            replicas=saved_deployment.replicas,
            containers=container_infos,
            pvcs=pvc_infos,
            labels=saved_deployment.labels,
            status=status_info,
        )

    def _resolve_image(self, payload: CloudDBCreateRequest, spec_image: str | None) -> str:
        """컨테이너 이미지 결정: 명시된 이미지 우선, 없으면 type에서 자동 결정"""
        if spec_image:
            return spec_image
        return CLOUD_DB_IMAGES[payload.type]

    def _build_cloud_db(
            self,
            name: str,
            namespace: str,
            payload: CloudDBCreateRequest,
            labels: dict,
    ) -> CloudDb:
        default_ports = CLOUD_DB_DEFAULT_PORTS[payload.type]
        container_specs = payload.containers or []

        # containers가 비어 있으면 type 기본값으로 단일 컨테이너 구성
        if not container_specs:
            container_specs = [CloudDBContainerSpec(name="main")]

        containers = []
        for spec in container_specs:
            disk = None
            if spec.disk:
                disk = CloudDbContainerDisk(
                    size=spec.disk.size,
                    mount_path=CLOUD_DB_MOUNT_PATHS[payload.type],
                    storage_class=spec.disk.storage_class,
                )
            containers.append(CloudDbContainer(
                name=spec.name,
                image=self._resolve_image(payload, spec.image),
                harbor_url=self._harbor.url,
                ports=spec.ports or default_ports,
                resources={
                    "requests": {
                        "cpu": spec.resources.requests.cpu,
                        "memory": spec.resources.requests.memory,
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
        return CloudDb(
            name=name,
            namespace=namespace,
            containers=containers,
            replicas=payload.replicas,
            labels=labels,
            annotations=payload.annotations or {},
        )

    def _build_k8s_containers(self, containers: List[CloudDbContainer]) -> List[Container]:
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
