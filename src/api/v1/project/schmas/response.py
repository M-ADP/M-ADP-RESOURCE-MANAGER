from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ServicePortResponse(BaseModel):
    """Service Port 응답 모델"""
    port: int
    target_port: int
    protocol: str
    name: Optional[str] = None
    node_port: Optional[int] = None


class ProjectCreateResponse(BaseModel):
    """Project 생성 응답 모델"""

    namespace: str
    resource_quota: str
    limits: Dict[str, str]


class ProjectDeleteResponse(BaseModel):
    """Project 삭제 응답 모델"""

    namespace: str
    resource_quota_deleted: bool


class ProjectPortOpenResponse(BaseModel):
    """Project 포트 개방 응답 모델 (Service 생성 결과)"""

    name: str
    namespace: str
    ports: List[ServicePortResponse]
    selector: Dict[str, str]
    service_type: str
    cluster_ip: Optional[str] = None
    external_ips: List[str] = Field(default_factory=list)


class ProjectPortCloseResponse(BaseModel):
    """Project 포트 정리 응답 모델"""

    service_closed: bool


class ProjectPortUpdateResponse(BaseModel):
    """Project 포트 수정 응답 모델 (Service 수정 결과)"""

    name: str
    namespace: str
    ports: List[ServicePortResponse]
    selector: Dict[str, str]
    service_type: str
    cluster_ip: Optional[str] = None
    external_ips: List[str] = Field(default_factory=list)
