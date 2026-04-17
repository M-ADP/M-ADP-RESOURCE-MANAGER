import asyncio
from typing import List
from fastapi import Depends

from src.core.project import ProjectId
from src.app.base_use_case import BaseUseCase
from src.common.util.unit_converter import UnitConverter
from src.common.util import NameConverter
from src.dependencies.kubernetes import get_deployment_manager, get_pvc_manager
from src.infra.kubernetes.managers.deployment import DeploymentManager
from src.infra.kubernetes.managers.persistentvolumeclaim import PersistentVolumeClaimManager
from src.app.monitoring.dto import (
    AppResourceStatusResponse,
    ResourceMetric,
    InstanceMetric,
)


class AppResourceStatusUseCase(BaseUseCase):
    """애플리케이션(Deployment) 리소스 상태 조회 UseCase"""

    def __init__(
        self,
        deployment_manager: DeploymentManager = Depends(get_deployment_manager),
        pvc_manager: PersistentVolumeClaimManager = Depends(get_pvc_manager),
    ):
        self.deployment_manager = deployment_manager
        self.pvc_manager = pvc_manager

    async def __call__(
        self, project_id: str, app_ids: List[str]
    ) -> List[AppResourceStatusResponse]:
        """여러 애플리케이션 리소스 상태 일괄 조회

        존재하지 않는 앱은 결과에서 제외됩니다.
        """
        results = await asyncio.gather(
            *[self._get_single(project_id, app_id) for app_id in app_ids],
            return_exceptions=True,
        )
        return [r for r in results if isinstance(r, AppResourceStatusResponse)]

    async def _get_single(
        self, project_id: str, app_id: str
    ) -> AppResourceStatusResponse:
        from src.app.app_deployment.exceptions import DeploymentNotFoundException

        namespace = ProjectId(project_id).namespace
        original_app_id = app_id
        app_id = NameConverter.to_k8s_name(app_id)
        deployment = await self.deployment_manager.get_deployment(
            name=app_id, namespace=namespace
        )
        if not deployment:
            raise DeploymentNotFoundException(name=app_id, namespace=namespace)

        replicas_limit = deployment.spec.replicas or 1
        replicas_used = (
            deployment.status.ready_replicas or 0 if deployment.status else 0
        )

        pod_requests = {"cpu": 0, "memory": 0}
        pod_limits = {"cpu": 0, "memory": 0}

        if deployment.spec.template.spec.containers:
            for container in deployment.spec.template.spec.containers:
                if not container.resources:
                    continue

                if container.resources.requests:
                    req = container.resources.requests
                    pod_requests["cpu"] += UnitConverter.parse_cpu_to_millicores(
                        req.get("cpu", "0")
                    )
                    pod_requests["memory"] += UnitConverter.parse_storage_to_bytes(
                        req.get("memory", "0")
                    )

                if container.resources.limits:
                    lim = container.resources.limits
                    pod_limits["cpu"] += UnitConverter.parse_cpu_to_millicores(
                        lim.get("cpu", "0")
                    )
                    pod_limits["memory"] += UnitConverter.parse_storage_to_bytes(
                        lim.get("memory", "0")
                    )

        disk_limit, disk_used = await self._get_pvc_disk_bytes(
            deployment, namespace
        )

        return AppResourceStatusResponse(
            app_id=original_app_id,
            project_id=project_id,
            cpu=self._create_resource_metric(
                pod_limits["cpu"] * replicas_limit,
                pod_requests["cpu"] * replicas_used,
                "cores",
                1000.0,
            ),
            memory=self._create_resource_metric(
                pod_limits["memory"] * replicas_limit,
                pod_requests["memory"] * replicas_used,
                "GiB",
                1024**3,
            ),
            disk=self._create_resource_metric(
                disk_limit,
                disk_used,
                "GiB",
                1024**3,
            ),
            instance=InstanceMetric(
                limit=replicas_limit,
                used=replicas_used,
                percentage=round((replicas_used / replicas_limit) * 100, 2)
                if replicas_limit > 0
                else 0.0,
            ),
        )

    async def _get_pvc_disk_bytes(self, deployment, namespace: str):
        """Deployment volumes에서 PVC를 찾아 limit(요청 용량)과 used(바인딩된 용량)를 반환"""
        volumes = (
            deployment.spec.template.spec.volumes
            if deployment.spec.template.spec
            else []
        ) or []

        pvc_names = [
            v.persistent_volume_claim.claim_name
            for v in volumes
            if v.persistent_volume_claim
        ]

        if not pvc_names:
            return 0, 0

        pvcs = await asyncio.gather(
            *[self.pvc_manager.get_pvc(name=name, namespace=namespace) for name in pvc_names],
            return_exceptions=True,
        )

        limit_bytes = 0
        used_bytes = 0
        for pvc in pvcs:
            if not pvc or isinstance(pvc, Exception):
                continue
            if pvc.spec and pvc.spec.resources and pvc.spec.resources.requests:
                limit_bytes += UnitConverter.parse_storage_to_bytes(
                    pvc.spec.resources.requests.get("storage", "0")
                )
            if pvc.status and pvc.status.phase == "Bound" and pvc.status.capacity:
                used_bytes += UnitConverter.parse_storage_to_bytes(
                    pvc.status.capacity.get("storage", "0")
                )

        return limit_bytes, used_bytes

    def _create_resource_metric(
        self, limit_val: int, used_val: int, unit: str, divider: float
    ) -> ResourceMetric:

        limit_display = round(limit_val / divider, 2)
        used_display = round(used_val / divider, 2)

        percentage = 0.0
        if limit_val > 0:
            percentage = round((used_val / limit_val) * 100, 2)

        return ResourceMetric(
            limit=str(limit_display),
            used=str(used_display),
            percentage=percentage,
            unit=unit,
        )
