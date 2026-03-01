from typing import Dict, List, Optional
from pydantic import BaseModel


class ConfigMapInfo(BaseModel):
    """ConfigMap 정보"""
    name: str
    namespace: str
    data: Dict[str, str] = {}
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}


class ConfigMapListResponse(BaseModel):
    """ConfigMap 목록 응답"""
    configmaps: List[ConfigMapInfo]
    total: int


class ConfigMapDetailResponse(BaseModel):
    """ConfigMap 상세 정보 응답"""
    configmap: ConfigMapInfo
