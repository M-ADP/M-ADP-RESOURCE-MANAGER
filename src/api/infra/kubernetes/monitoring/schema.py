"""Monitoring API 스키마"""

from pydantic import BaseModel, Field


class ResourceMetricsInfo(BaseModel):
    """리소스 메트릭 정보"""
    total: float = Field(..., description="클러스터 총 리소스")
    allocated: float = Field(..., description="ResourceQuota로 할당된 리소스")
    allocation_ratio: float = Field(..., description="할당 비율 (%)")
    threshold: int = Field(..., description="임계값 (%)")
    exceeds_threshold: bool = Field(..., description="임계값 초과 여부")
    unit: str = Field(..., description="단위")


class ClusterResourceStatusResponse(BaseModel):
    """클러스터 리소스 상태 응답"""
    cpu: ResourceMetricsInfo
    memory: ResourceMetricsInfo
    storage: ResourceMetricsInfo
    node_count: int = Field(..., description="클러스터 노드 수")
    namespace_count: int = Field(..., description="ResourceQuota가 있는 네임스페이스 수")


class ThresholdConfigResponse(BaseModel):
    """임계값 설정 응답"""
    cpu: int = Field(..., description="CPU 임계값 (%)")
    memory: int = Field(..., description="Memory 임계값 (%)")
    storage: int = Field(..., description="Storage 임계값 (%)")
