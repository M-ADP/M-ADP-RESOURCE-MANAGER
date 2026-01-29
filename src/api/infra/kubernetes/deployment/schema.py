from typing import Dict, List, Optional
from pydantic import BaseModel


class ContainerInfo(BaseModel):
    """Container 정보"""
    name: str
    image: Optional[str] = None


class DeploymentStatusInfo(BaseModel):
    """Deployment 상태 정보"""
    replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    available_replicas: Optional[int] = None
    updated_replicas: Optional[int] = None


class DeploymentInfo(BaseModel):
    """Deployment 정보"""
    name: str
    namespace: str
    replicas: int
    containers: List[ContainerInfo]
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    selector_labels: Dict[str, str] = {}
    status: Optional[DeploymentStatusInfo] = None


class DeploymentListResponse(BaseModel):
    """Deployment 목록 응답"""
    deployments: List[DeploymentInfo]
    total: int


class DeploymentDetailResponse(BaseModel):
    """Deployment 상세 정보 응답"""
    deployment: DeploymentInfo
