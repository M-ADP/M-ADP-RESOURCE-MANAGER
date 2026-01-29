from typing import Dict, List, Optional
from pydantic import BaseModel


class LimitRangeItemInfo(BaseModel):
    """LimitRange Item 정보"""
    type: str
    default: Optional[Dict[str, str]] = None
    default_request: Optional[Dict[str, str]] = None
    max: Optional[Dict[str, str]] = None
    min: Optional[Dict[str, str]] = None
    max_limit_request_ratio: Optional[Dict[str, str]] = None


class LimitRangeInfo(BaseModel):
    """LimitRange 정보"""
    name: str
    namespace: str
    limits: List[LimitRangeItemInfo] = []
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}


class LimitRangeListResponse(BaseModel):
    """LimitRange 목록 응답"""
    limit_ranges: List[LimitRangeInfo]
    total: int


class LimitRangeDetailResponse(BaseModel):
    """LimitRange 상세 정보 응답"""
    limit_range: LimitRangeInfo
