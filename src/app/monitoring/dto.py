from typing import Optional
from pydantic import BaseModel, Field

class ResourceMetric(BaseModel):
    """리소스 메트릭 (CPU, Memory, Disk)"""
    limit: Optional[str] = Field(None, description="리소스 제한량 (Limit)")
    used: Optional[str] = Field(None, description="현재 사용량 (Request/Used)")
    percentage: Optional[float] = Field(None, description="사용률 (%)")
    unit: str = Field(..., description="단위 (cores, GiB)")

class InstanceMetric(BaseModel):
    """인스턴스(Pod) 메트릭"""
    limit: int = Field(..., description="최대 인스턴스 수 (Replicas). -1은 무제한.")
    used: int = Field(..., description="현재 인스턴스 수 (Ready Replicas)")
    percentage: Optional[float] = Field(None, description="가용률 (%)")

class ProjectResourceStatusResponse(BaseModel):
    """프로젝트 리소스 상태 응답"""
    project_id: str = Field(..., description="프로젝트 ID (Namespace)")
    cpu: ResourceMetric
    memory: ResourceMetric
    disk: ResourceMetric
    instance: InstanceMetric

class AppResourceStatusResponse(BaseModel):
    """애플리케이션 리소스 상태 응답"""
    app_id: str = Field(..., description="애플리케이션 ID (Deployment Name)")
    project_id: str = Field(..., description="프로젝트 ID (Namespace)")
    cpu: ResourceMetric
    memory: ResourceMetric
    disk: ResourceMetric
    instance: InstanceMetric
