"""Project 스키마"""

from enum import Enum
from typing import Dict, Optional, Literal

from pydantic import BaseModel, Field


class ProtocolType(str, Enum):
    """Kubernetes Service 프로토콜 타입"""
    TCP = "TCP"
    UDP = "UDP"
    SCTP = "SCTP"


class ServiceType(str, Enum):
    """Kubernetes Service 타입"""
    CLUSTER_IP = "ClusterIP"
    NODE_PORT = "NodePort"
    LOAD_BALANCER = "LoadBalancer"


class ProjectCreateRequest(BaseModel):
    """Project 생성 요청 모델"""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    cpu: str = "100m" # 0.1v
    memory: str = "32Mi" # 32MB
    disk: str = "32Mi" # 32MB


class ProjectPortOpenRequest(BaseModel):
    """Project 포트 개방 요청 모델"""

    service_id: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r'^[a-z][a-z0-9-]*$',
        description="서비스 ID (소문자로 시작, 소문자/숫자/하이픈만 허용)"
    )
    service_name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r'^[a-z][a-z0-9-]*$',
        description="서비스 이름 (소문자로 시작, 소문자/숫자/하이픈만 허용)"
    )
    target_deployment_name: str = Field(..., min_length=1)
    port: int = Field(..., gt=0, le=65535)
    target_port: int = Field(..., gt=0, le=65535)
    protocol: ProtocolType = Field(default=ProtocolType.TCP, description="프로토콜 (TCP, UDP, SCTP)")
    service_type: ServiceType = Field(default=ServiceType.CLUSTER_IP, description="서비스 타입 (ClusterIP, NodePort, LoadBalancer)")


class ProjectPortUpdateRequest(BaseModel):
    """Project 포트 수정 요청 모델"""

    service_id: str = Field(..., min_length=1) # 서비스 이름 추가
    service_name: Optional[str] = Field(None, min_length=1)
    target_deployment_name: Optional[str] = Field(None, min_length=1)
    target_port: Optional[int] = Field(None, gt=0, le=65535)
    protocol: Optional[ProtocolType] = Field(default=ProtocolType.TCP, description="프로토콜 (TCP, UDP, SCTP)")
    service_type: Optional[ServiceType] = Field(default=ServiceType.CLUSTER_IP, description="서비스 타입 (ClusterIP, NodePort, LoadBalancer)")


class ProjectDnsCreateRequest(BaseModel):
    """Project DNS 생성 요청 모델"""
    
    subdomain: str = Field(..., min_length=1)


class ProjectDnsUpdateRequest(BaseModel):


    """Project DNS 수정 요청 모델"""





    new_subdomain: str = Field(..., min_length=1)








class ProjectDnsPortBindRequest(BaseModel):


    """Project DNS 포트 바인딩 요청 모델"""





    target_service_id: str = Field(..., min_length=1)








class ProjectResourceUpdateRequest(BaseModel):


    """Project 리소스 할당량 수정 요청 모델"""





    cpu: Optional[str] = None


    memory: Optional[str] = None


    disk: Optional[str] = None




