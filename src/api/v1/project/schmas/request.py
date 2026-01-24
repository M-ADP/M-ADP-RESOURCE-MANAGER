"""Project 스키마"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """Project 생성 요청 모델"""

    name: str = Field(..., min_length=1)
    cpu: str = "100m" # 0.1v
    memory: str = "32Mi" # 32MB
    disk: str = "32Mi" # 32MB


class ProjectPortOpenRequest(BaseModel):
    """Project 포트 개방 요청 모델"""

    service_name: str = Field(..., min_length=1)
    target_deployment_name: str = Field(..., min_length=1)
    port: int = Field(..., gt=0, le=65535)
    target_port: int = Field(..., gt=0, le=65535)
    protocol: str = "TCP"
    service_type: str = "ClusterIP" # ClusterIP, NodePort, LoadBalancer


class ProjectPortUpdateRequest(BaseModel):
    """Project 포트 수정 요청 모델"""

    service_name: str = Field(..., min_length=1) # 서비스 이름 추가
    target_deployment_name: Optional[str] = Field(None, min_length=1)
    target_port: Optional[int] = Field(None, gt=0, le=65535)
    protocol: Optional[str] = "TCP"
    service_type: Optional[str] = "ClusterIP" # ClusterIP, NodePort, LoadBalancer