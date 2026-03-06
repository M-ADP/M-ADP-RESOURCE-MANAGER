from typing import Dict, List, Optional
from pydantic import BaseModel


class ServicePortInfo(BaseModel):
    """Service Port 정보"""
    port: int
    target_port: int
    protocol: str = "TCP"
    name: Optional[str] = None
    node_port: Optional[int] = None


class ServiceInfo(BaseModel):
    """Service 정보"""
    name: str
    namespace: str
    ports: List[ServicePortInfo]
    selector: Dict[str, str] = {}
    service_type: str = "ClusterIP"
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    cluster_ip: Optional[str] = None
    external_ips: List[str] = []


class ServiceListResponse(BaseModel):
    """Service 목록 응답"""
    services: List[ServiceInfo]
    total: int


class ServiceDetailResponse(BaseModel):
    """Service 상세 정보 응답"""
    service: ServiceInfo
