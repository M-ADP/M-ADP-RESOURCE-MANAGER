"""클러스터 리소스 상태 조회 UseCase"""

from dataclasses import dataclass
from typing import Optional
from fastapi import Depends

from src.app.base_use_case import BaseUseCase
from src.common.config.monitoring import MonitoringConfig
from src.common.util.unit_converter import UnitConverter
from src.infra.kubernetes.managers.node import NodeManager
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from .exceptions import ClusterResourceCalculationException


@dataclass
class ResourceMetrics:
    """단일 리소스 타입의 메트릭"""
    total: float           # 클러스터 총 리소스
    allocated: float       # ResourceQuota로 할당된 리소스
    allocation_ratio: float  # 할당 비율 (0-100)
    threshold: int         # 임계값 (0-100)
    exceeds_threshold: bool  # 임계값 초과 여부
    unit: str              # 단위 (cores, GiB)


@dataclass
class ClusterResourceStatus:
    """클러스터 리소스 상태"""
    cpu: ResourceMetrics
    memory: ResourceMetrics
    storage: ResourceMetrics
    node_count: int
    namespace_count: int  # ResourceQuota가 있는 네임스페이스 수


class ClusterResourceStatusUseCase(BaseUseCase):
    """클러스터 리소스 할당 비율 조회 UseCase
    
    클러스터 전체 리소스 대비 ResourceQuota 할당 비율을 계산합니다.
    """

    def __init__(
        self,
        node_manager: NodeManager,
        resource_quota_manager: ResourceQuotaManager,
        config: Optional[MonitoringConfig] = None,
    ):
        self.node_manager = node_manager
        self.resource_quota_manager = resource_quota_manager
        self.config = config or MonitoringConfig()

    async def __call__(self) -> ClusterResourceStatus:
        """클러스터 리소스 상태 계산 및 반환"""
        try:
            # 1. 클러스터 총 리소스 조회 (모든 노드의 allocatable 합계)
            cluster_resources = await self.node_manager.get_cluster_allocatable_resources()
            nodes = await self.node_manager.list_nodes()
            
            # 2. 모든 ResourceQuota의 hard limits 합계 조회
            resource_quotas = await self.resource_quota_manager.list_resource_quotas(
                namespace=None  # 모든 네임스페이스
            )
            
            allocated = self._sum_resource_quota_limits(resource_quotas)
            
            # 3. 할당 비율 계산
            cpu_status = self._calculate_resource_metrics(
                total_value=cluster_resources["cpu_millicores"],
                allocated_value=allocated["cpu_millicores"],
                threshold=self.config.threshold_cpu,
                to_display_unit=UnitConverter.millicores_to_cores,
                unit="cores",
            )
            
            memory_status = self._calculate_resource_metrics(
                total_value=cluster_resources["memory_bytes"],
                allocated_value=allocated["memory_bytes"],
                threshold=self.config.threshold_memory,
                to_display_unit=UnitConverter.bytes_to_gibibytes,
                unit="GiB",
            )
            
            storage_status = self._calculate_resource_metrics(
                total_value=cluster_resources["storage_bytes"],
                allocated_value=allocated["storage_bytes"],
                threshold=self.config.threshold_storage,
                to_display_unit=UnitConverter.bytes_to_gibibytes,
                unit="GiB",
            )
            
            # 4. 고유 네임스페이스 수 계산
            unique_namespaces = set(
                rq.metadata.namespace for rq in resource_quotas 
                if rq.metadata and rq.metadata.namespace
            )
            
            return ClusterResourceStatus(
                cpu=cpu_status,
                memory=memory_status,
                storage=storage_status,
                node_count=len(nodes),
                namespace_count=len(unique_namespaces),
            )
        
        except Exception as e:
            raise ClusterResourceCalculationException(reason=str(e))

    def _sum_resource_quota_limits(self, resource_quotas: list) -> dict:
        """모든 ResourceQuota의 hard limits 합계 계산
        
        Args:
            resource_quotas: V1ResourceQuota 객체 리스트
        
        Returns:
            {
                "cpu_millicores": int,
                "memory_bytes": int,
                "storage_bytes": int,
            }
        """
        total_cpu_millicores = 0
        total_memory_bytes = 0
        total_storage_bytes = 0
        
        for rq in resource_quotas:
            if rq.spec and rq.spec.hard:
                hard = rq.spec.hard
                
                # CPU: "requests.cpu" or "limits.cpu" or "cpu"
                cpu_value = hard.get("requests.cpu") or hard.get("limits.cpu") or hard.get("cpu")
                if cpu_value:
                    total_cpu_millicores += UnitConverter.parse_cpu_to_millicores(cpu_value)
                
                # Memory: "requests.memory" or "limits.memory" or "memory"
                memory_value = hard.get("requests.memory") or hard.get("limits.memory") or hard.get("memory")
                if memory_value:
                    total_memory_bytes += UnitConverter.parse_storage_to_bytes(memory_value)
                
                # Storage: "requests.storage" or "requests.ephemeral-storage"
                storage_value = hard.get("requests.storage") or hard.get("requests.ephemeral-storage")
                if storage_value:
                    total_storage_bytes += UnitConverter.parse_storage_to_bytes(storage_value)
        
        return {
            "cpu_millicores": total_cpu_millicores,
            "memory_bytes": total_memory_bytes,
            "storage_bytes": total_storage_bytes,
        }

    def _calculate_resource_metrics(
        self,
        total_value: int,
        allocated_value: int,
        threshold: int,
        to_display_unit: callable,
        unit: str,
    ) -> ResourceMetrics:
        """리소스 메트릭 계산
        
        Args:
            total_value: 클러스터 총 리소스 (원시 단위)
            allocated_value: 할당된 리소스 (원시 단위)
            threshold: 임계값 (%)
            to_display_unit: 표시 단위 변환 함수
            unit: 표시 단위 문자열
        
        Returns:
            ResourceMetrics 객체
        """
        # 0으로 나누기 방지
        if total_value == 0:
            allocation_ratio = 0.0
        else:
            allocation_ratio = (allocated_value / total_value) * 100
        
        return ResourceMetrics(
            total=round(to_display_unit(total_value), 2),
            allocated=round(to_display_unit(allocated_value), 2),
            allocation_ratio=round(allocation_ratio, 2),
            threshold=threshold,
            exceeds_threshold=allocation_ratio > threshold,
            unit=unit,
        )
