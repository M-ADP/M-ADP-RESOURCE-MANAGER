from typing import Dict, List, Optional
from pydantic import BaseModel


class StatefulSetStatusInfo(BaseModel):
    """StatefulSet 상태 정보"""
    replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    current_replicas: Optional[int] = None
    updated_replicas: Optional[int] = None


class StatefulSetInfo(BaseModel):
    """StatefulSet 정보"""
    name: str
    namespace: str
    replicas: int
    service_name: Optional[str] = None
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    status: Optional[StatefulSetStatusInfo] = None


class StatefulSetListResponse(BaseModel):
    """StatefulSet 목록 응답"""
    statefulsets: List[StatefulSetInfo]
    total: int


class StatefulSetDetailResponse(BaseModel):
    """StatefulSet 상세 정보 응답"""
    statefulset: StatefulSetInfo
