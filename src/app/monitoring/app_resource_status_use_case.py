import asyncio
from typing import List, Dict

from fastapi import Depends

from src.core.project import ProjectId
from src.app.base_use_case import BaseUseCase
from src.common.util.unit_converter import UnitConverter
from src.common.util import NameConverter
from src.dependencies.kubernetes import (
    get_deployment_manager,
    get_pvc_manager,
    get_pod_manager,
    get_node_manager,
)
from src.infra.kubernetes.managers.deployment import DeploymentManager
from src.infra.kubernetes.managers.persistentvolumeclaim import PersistentVolumeClaimManager
from src.infra.kubernetes.managers.pod import PodManager
from src.infra.kubernetes.managers.node import NodeManager
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
        pod_manager: PodManager = Depends(get_pod_manager),
        node_manager: NodeManager = Depends(get_node_manager),
    ):
        self.deployment_manager = deployment_manager
        self.pvc_manager = pvc_manager
        self.pod_manager = pod_manager
        self.node_manager = node_manager

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

        disk_limit, disk_used = await self._get_disk_bytes(
            deployment=deployment,
            namespace=namespace,
            app_id=app_id,
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
            disk=self._create_resource_metric(disk_limit, disk_used, "GiB", 1024**3),
            instance=InstanceMetric(
                limit=replicas_limit,
                used=replicas_used,
                percentage=round((replicas_used / replicas_limit) * 100, 2)
                if replicas_limit > 0
                else 0.0,
            ),
        )

    async def _get_disk_bytes(self, deployment, namespace: str, app_id: str):
        """disk limit/used(bytes) 반환.

        1순위: kubelet stats/summary → 실제 사용량
        2순위: PVC spec/status → 프로비저닝 용량 (fallback)
        """
        volumes = (deployment.spec.template.spec.volumes or [])
        pvc_volume_names = {v.name for v in volumes if v.persistent_volume_claim}

        if not pvc_volume_names:
            return 0, 0

        # Running Pod를 label selector로 조회
        pods = await self.pod_manager.list_pods(
            namespace=namespace,
            label_selector=f"app_deployment={app_id}",
        )
        running_pods = [
            p for p in pods
            if p.status and p.status.phase == "Running" and p.spec.node_name
        ]

        if running_pods:
            limit_bytes, used_bytes = await self._stats_from_kubelet(
                running_pods, pvc_volume_names
            )
            if limit_bytes > 0:
                return limit_bytes, used_bytes

        # fallback: PVC spec/status
        return await self._pvc_disk_bytes(deployment, namespace)

    async def _stats_from_kubelet(self, running_pods, pvc_volume_names) -> tuple:
        """kubelet stats/summary에서 volume 실사용량 집계."""
        # 노드 중복 제거 — 같은 노드의 pod는 stats 1번 호출로 처리
        node_pods: Dict[str, list] = {}
        for pod in running_pods:
            node_pods.setdefault(pod.spec.node_name, []).append(pod)

        node_names = list(node_pods.keys())
        stats_list = await asyncio.gather(
            *[self.node_manager.get_node_volume_stats(n) for n in node_names],
            return_exceptions=True,
        )

        limit_bytes = 0
        used_bytes = 0

        for node_name, node_stats in zip(node_names, stats_list):
            if isinstance(node_stats, Exception) or not node_stats:
                continue

            pod_stats_index = {
                (s["podRef"]["name"], s["podRef"]["namespace"]): s
                for s in node_stats.get("pods", [])
                if "podRef" in s
            }

            for pod in node_pods[node_name]:
                key = (pod.metadata.name, pod.metadata.namespace)
                pod_stat = pod_stats_index.get(key)
                if not pod_stat:
                    continue

                for vol in pod_stat.get("volume", []):
                    if vol.get("name") in pvc_volume_names:
                        limit_bytes += vol.get("capacityBytes", 0)
                        used_bytes += vol.get("usedBytes", 0)

        return limit_bytes, used_bytes

    async def _pvc_disk_bytes(self, deployment, namespace: str) -> tuple:
        """PVC spec/status 기반 fallback. limit=요청용량, used=바인딩된 용량."""
        volumes = (deployment.spec.template.spec.volumes or [])
        pvc_names = [
            v.persistent_volume_claim.claim_name
            for v in volumes
            if v.persistent_volume_claim
        ]

        pvcs = await asyncio.gather(
            *[self.pvc_manager.get_pvc(name=n, namespace=namespace) for n in pvc_names],
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
