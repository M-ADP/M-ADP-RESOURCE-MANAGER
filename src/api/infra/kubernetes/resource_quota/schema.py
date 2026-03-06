from typing import Dict, List, Optional
from pydantic import BaseModel


class ResourceQuotaInfo(BaseModel):
    """ResourceQuota 정보"""
    name: str
    namespace: str
    hard_limits: Dict[str, str] = {}
    used: Dict[str, str] = {}
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}


class ResourceQuotaListResponse(BaseModel):
    """ResourceQuota 목록 응답"""
    resource_quotas: List[ResourceQuotaInfo]
    total: int


class ResourceQuotaDetailResponse(BaseModel):
    """ResourceQuota 상세 정보 응답"""
    resource_quota: ResourceQuotaInfo
