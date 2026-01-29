from typing import Dict, List, Optional
from pydantic import BaseModel


class JobStatusInfo(BaseModel):
    """Job 상태 정보"""
    active: Optional[int] = None
    succeeded: Optional[int] = None
    failed: Optional[int] = None
    start_time: Optional[str] = None
    completion_time: Optional[str] = None


class JobInfo(BaseModel):
    """Job 정보"""
    name: str
    namespace: str
    completions: Optional[int] = None
    parallelism: Optional[int] = None
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    status: Optional[JobStatusInfo] = None


class JobListResponse(BaseModel):
    """Job 목록 응답"""
    jobs: List[JobInfo]
    total: int


class JobDetailResponse(BaseModel):
    """Job 상세 정보 응답"""
    job: JobInfo
