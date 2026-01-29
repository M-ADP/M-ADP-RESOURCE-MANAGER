from typing import Dict, List, Optional
from pydantic import BaseModel


class PVCInfo(BaseModel):
    """PersistentVolumeClaim 정보"""
    name: str
    namespace: str
    storage_class: Optional[str] = None
    access_modes: List[str] = []
    capacity: Optional[str] = None
    requested_storage: Optional[str] = None
    phase: Optional[str] = None
    volume_name: Optional[str] = None
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}


class PVCListResponse(BaseModel):
    """PVC 목록 응답"""
    pvcs: List[PVCInfo]
    total: int


class PVCDetailResponse(BaseModel):
    """PVC 상세 정보 응답"""
    pvc: PVCInfo
