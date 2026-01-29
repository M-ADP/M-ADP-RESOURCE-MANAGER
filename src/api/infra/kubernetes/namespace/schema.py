from typing import Dict, List, Optional
from pydantic import BaseModel


class NamespaceInfo(BaseModel):
    """Namespace 정보"""
    name: str
    status: Optional[str] = None
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    created_at: Optional[str] = None


class NamespaceListResponse(BaseModel):
    """Namespace 목록 응답"""
    namespaces: List[NamespaceInfo]
    total: int


class NamespaceDetailResponse(BaseModel):
    """Namespace 상세 정보 응답"""
    namespace: NamespaceInfo
