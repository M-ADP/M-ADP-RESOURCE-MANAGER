import asyncio
from typing import Dict, Any, Optional
from fastapi import Depends
from src.core.project import ProjectId

from src.app.base_use_case import BaseUseCase
from src.common.util.unit_converter import UnitConverter
from src.dependencies.kubernetes import get_resource_quota_manager, get_pod_manager, get_node_manager
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from src.infra.kubernetes.managers.pod import PodManager
from src.infra.kubernetes.managers.node import NodeManager
from src.app.monitoring.dto import ProjectResourceStatusResponse, ResourceMetric, InstanceMetric
from src.app.project.exceptions import ProjectNotFoundException


class ProjectResourceStatusUseCase(BaseUseCase):
    """프로젝트(Namespace) 리소스 상태 조회 UseCase"""

    def __init__(
        self,
        resource_quota_manager: ResourceQuotaManager = Depends(get_resource_quota_manager),
        pod_manager: PodManager = Depends(get_pod_manager),
        node_manager: NodeManager = Depends(get_node_manager),
    ):
        self.resource_quota_manager = resource_quota_manager
        self.pod_manager = pod_manager
        self.node_manager = node_manager

    async def __call__(self, project_id: str) -> ProjectResourceStatusResponse:
        """프로젝트 리소스 상태 조회"""
        
        # ResourceQuota 조회
        # 이름은 보통 namespace와 동일하거나, 특정 이름 규칙을 따름
        # ProjectCreateUseCase를 보면, ResourceQuota 이름이 project_name(namespace name)과 같음?
        # 아니, ProjectCreateUseCase에서 `ResourceQuota.for_project` 사용.
        # `ResourceQuota.for_project` 내부를 보지 못했지만, 보통 namespace와 동일하게 하거나 'default' 등으로 함.
        # 여기서는 project_id(namespace)와 동일한 이름의 ResourceQuota를 찾는다고 가정하거나,
        # 해당 namespace의 모든 ResourceQuota를 합산해야 함.
        
        namespace = ProjectId(project_id).namespace
        try:
            quotas = await self.resource_quota_manager.list_resource_quotas(namespace=namespace)
        except Exception:
            raise ProjectNotFoundException()

        if not quotas:
            return self._create_empty_response(project_id)

        total_hard = {}
        total_used = {}

        for rq in quotas:
            if rq.spec and rq.spec.hard:
                self._accumulate_resources(total_hard, rq.spec.hard)
            if rq.status and rq.status.used:
                self._accumulate_resources(total_used, rq.status.used)

        # 실시간 CPU/Memory: metrics-server 우선, 실패 시 ResourceQuota status.used fallback
        pod_metrics = await self.pod_manager.get_namespace_pod_metrics(namespace=namespace)
        if pod_metrics is not None:
            real_used = {"cpu": pod_metrics["cpu_millicores"], "memory": pod_metrics["memory_bytes"]}
        else:
            real_used = total_used

        disk_limit, disk_used = await self._get_disk_bytes(namespace, total_hard)

        disk_limit_display = round(disk_limit / 1024**3, 2) if disk_limit else 0
        disk_used_display = round(disk_used / 1024**3, 2) if disk_used else 0
        disk_percentage = round((disk_used / disk_limit) * 100, 2) if disk_limit > 0 else 0.0

        return ProjectResourceStatusResponse(
            project_id=project_id,
            cpu=self._create_resource_metric(
                total_hard, real_used, "cpu", UnitConverter.parse_cpu_to_millicores, "cores", 1000.0
            ),
            memory=self._create_resource_metric(
                total_hard, real_used, "memory", UnitConverter.parse_storage_to_bytes, "GiB", 1024**3
            ),
            disk=ResourceMetric(
                limit=str(disk_limit_display) if disk_limit else "Unlimited",
                used=str(disk_used_display),
                percentage=disk_percentage,
                unit="GiB",
            ),
            instance=self._create_instance_metric(total_hard, total_used, "pods"),
        )

    async def _get_disk_bytes(self, namespace: str, total_hard: Dict[str, Any]):
        """네임스페이스 내 모든 파드의 볼륨 실사용량 집계.

        1순위: kubelet stats/summary
        2순위: ResourceQuota hard limit 값 그대로 (limit=used fallback)
        """
        limit_bytes = total_hard.get("requests.storage", 0) or total_hard.get("storage", 0)

        pods = await self.pod_manager.list_pods(namespace=namespace)
        running_pods = [
            p for p in pods
            if p.status and p.status.phase == "Running" and p.spec and p.spec.node_name
        ]

        if not running_pods:
            return limit_bytes, 0

        node_pods: Dict[str, list] = {}
        for pod in running_pods:
            node_pods.setdefault(pod.spec.node_name, []).append(pod)

        stats_list = await asyncio.gather(
            *[self.node_manager.get_node_volume_stats(n) for n in node_pods],
            return_exceptions=True,
        )

        used_bytes = 0
        for node_name, node_stats in zip(node_pods, stats_list):
            if isinstance(node_stats, Exception) or not node_stats:
                continue

            pod_stats_index = {
                (s["podRef"]["name"], s["podRef"]["namespace"]): s
                for s in node_stats.get("pods", [])
                if "podRef" in s
            }

            for pod in node_pods[node_name]:
                pod_stat = pod_stats_index.get((pod.metadata.name, pod.metadata.namespace))
                if not pod_stat:
                    continue
                for vol in pod_stat.get("volume", []):
                    used_bytes += vol.get("usedBytes", 0)

        return limit_bytes, used_bytes

    def _accumulate_resources(self, target: Dict[str, Any], source: Dict[str, Any]):
        """리소스 합산 (단위 변환 필요 없음, 문자열 그대로 처리 불가하므로 변환 후 합산해야 함)"""
        keys_to_process = ["cpu", "requests.cpu", "limits.cpu", 
                           "memory", "requests.memory", "limits.memory",
                           "pods", "requests.storage", "ephemeral-storage"]
        
        for key, value in source.items():
            if key not in keys_to_process and "storage" not in key:
                continue

            # 값 파싱
            if "cpu" in key:
                parsed = UnitConverter.parse_cpu_to_millicores(value)
            elif "pods" in key or "count" in key:
                parsed = int(value)
            else: # memory, storage
                parsed = UnitConverter.parse_storage_to_bytes(value)
            
            # 합산 (기존 값이 없으면 할당, 있으면 합산)
            # 주의: ResourceQuota가 여러 개일 때 '가장 엄격한 것'이 적용되지만,
            # 여기서는 단순 모니터링 합산으로 처리 중.
            # 만약 Limit이 없는 경우(무제한)는 키가 아예 안 들어옴.
            current = target.get(key, 0)
            target[key] = current + parsed
            
            # 키가 존재한다는 표시를 위해 0이라도 저장해야 함 (이미 target[key] = ... 로 저장됨)

    def _create_resource_metric(
        self, 
        hard: Dict[str, Any], 
        used: Dict[str, Any], 
        resource_type: str, 
        parser, 
        unit: str, 
        divider: float
    ) -> ResourceMetric:
        
        # Limit (Hard)
        limit_val = 0
        if resource_type == "cpu":
            limit_val = hard.get("limits.cpu", 0) or hard.get("requests.cpu", 0) or hard.get("cpu", 0)
        elif resource_type == "memory":
            limit_val = hard.get("limits.memory", 0) or hard.get("requests.memory", 0) or hard.get("memory", 0)
        elif resource_type == "requests.storage":
            limit_val = hard.get("requests.storage", 0) or hard.get("storage", 0)
        
        # Used
        used_val = 0
        if resource_type == "cpu":
            used_val = used.get("limits.cpu", 0) or used.get("requests.cpu", 0) or used.get("cpu", 0)
        elif resource_type == "memory":
            used_val = used.get("limits.memory", 0) or used.get("requests.memory", 0) or used.get("memory", 0)
        elif resource_type == "requests.storage":
            used_val = used.get("requests.storage", 0) or used.get("storage", 0)
            
        limit_display = round(limit_val / divider, 2) if limit_val else 0
        used_display = round(used_val / divider, 2) if used_val else 0
        
        percentage = 0.0
        if limit_val > 0:
            percentage = round((used_val / limit_val) * 100, 2)
            
        return ResourceMetric(
            limit=str(limit_display) if limit_val else "Unlimited",
            used=str(used_display),
            percentage=percentage,
            unit=unit
        )

    def _create_instance_metric(self, hard: Dict[str, Any], used: Dict[str, Any], key: str) -> InstanceMetric:
        # 키가 존재하지 않으면 무제한(-1)으로 처리
        if key not in hard:
            return InstanceMetric(
                limit=-1,
                used=int(used.get(key, 0)),
                percentage=0.0
            )

        limit_val = hard.get(key, 0)
        used_val = used.get(key, 0)
        
        percentage = 0.0
        if limit_val > 0:
            percentage = round((used_val / limit_val) * 100, 2)
            
        return InstanceMetric(
            limit=int(limit_val),
            used=int(used_val),
            percentage=percentage
        )

    def _create_empty_response(self, project_id: str) -> ProjectResourceStatusResponse:
        empty_metric = ResourceMetric(limit="Unlimited", used="0", percentage=0.0, unit="")
        empty_instance = InstanceMetric(limit=0, used=0, percentage=0.0)
        return ProjectResourceStatusResponse(
            project_id=project_id,
            cpu=empty_metric.model_copy(update={"unit": "cores"}),
            memory=empty_metric.model_copy(update={"unit": "GiB"}),
            disk=empty_metric.model_copy(update={"unit": "GiB"}),
            instance=empty_instance,
        )
