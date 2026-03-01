"""Kubernetes Cluster Monitoring API"""

from fastapi import APIRouter, Depends

from src.api.infra.kubernetes.monitoring.schema import (
    ClusterResourceStatusResponse,
    ResourceMetricsInfo,
    ThresholdConfigResponse,
)
from src.app.monitoring import ClusterResourceStatusUseCase
from src.common.config.monitoring import MonitoringConfig
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_node_manager, get_resource_quota_manager
from src.infra.kubernetes.managers.node import NodeManager
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager

monitoring_router = APIRouter(
    prefix="/monitoring",
    tags=["kubernetes-monitoring"],
)


async def get_cluster_resource_status_use_case(
    node_manager: NodeManager = Depends(get_node_manager),
    resource_quota_manager: ResourceQuotaManager = Depends(get_resource_quota_manager),
) -> ClusterResourceStatusUseCase:
    """ClusterResourceStatusUseCase 의존성 주입"""
    return ClusterResourceStatusUseCase(
        node_manager=node_manager,
        resource_quota_manager=resource_quota_manager,
    )


@monitoring_router.get(
    "/cluster/resources",
    response_model=SuccessResponse[ClusterResourceStatusResponse],
    summary="클러스터 리소스 할당 상태 조회",
    description="클러스터 전체 리소스 대비 ResourceQuota 할당 비율을 조회합니다.",
)
async def get_cluster_resource_status(
    use_case: ClusterResourceStatusUseCase = Depends(get_cluster_resource_status_use_case),
):
    """클러스터 리소스 할당 비율 조회
    
    - CPU, Memory, Storage의 할당 비율 계산
    - 각 리소스별 임계값 초과 여부 표시
    - 노드 수 및 네임스페이스 수 정보 포함
    """
    status = await use_case()
    
    response = ClusterResourceStatusResponse(
        cpu=ResourceMetricsInfo(
            total=status.cpu.total,
            allocated=status.cpu.allocated,
            allocation_ratio=status.cpu.allocation_ratio,
            threshold=status.cpu.threshold,
            exceeds_threshold=status.cpu.exceeds_threshold,
            unit=status.cpu.unit,
        ),
        memory=ResourceMetricsInfo(
            total=status.memory.total,
            allocated=status.memory.allocated,
            allocation_ratio=status.memory.allocation_ratio,
            threshold=status.memory.threshold,
            exceeds_threshold=status.memory.exceeds_threshold,
            unit=status.memory.unit,
        ),
        storage=ResourceMetricsInfo(
            total=status.storage.total,
            allocated=status.storage.allocated,
            allocation_ratio=status.storage.allocation_ratio,
            threshold=status.storage.threshold,
            exceeds_threshold=status.storage.exceeds_threshold,
            unit=status.storage.unit,
        ),
        node_count=status.node_count,
        namespace_count=status.namespace_count,
    )
    
    return SuccessResponse(
        message="Cluster resource status retrieved successfully",
        data=response,
    )


@monitoring_router.get(
    "/config/thresholds",
    response_model=SuccessResponse[ThresholdConfigResponse],
    summary="현재 임계값 설정 조회",
    description="현재 설정된 리소스 모니터링 임계값을 조회합니다.",
)
async def get_threshold_config():
    """현재 임계값 설정 조회"""
    config = MonitoringConfig()
    
    response = ThresholdConfigResponse(
        cpu=config.threshold_cpu,
        memory=config.threshold_memory,
        storage=config.threshold_storage,
    )
    
    return SuccessResponse(
        message="Threshold configuration retrieved successfully",
        data=response,
    )
