from pydantic import BaseModel
from typing import List, Optional


class PodLogInfo(BaseModel):
    """Pod 로그 정보"""
    pod_name: str
    logs: str


class AppLogsResponse(BaseModel):
    """App 로그 응답"""
    deployment_name: str
    namespace: str
    pod_logs: List[PodLogInfo]


class JenkinsBuildLogItem(BaseModel):
    """Jenkins 빌드 로그 항목"""
    number: int
    result: Optional[str] = None
    timestamp: int
    duration: int
    url: Optional[str] = None


class JenkinsBuildLogListResponse(BaseModel):
    """Jenkins 빌드 로그 목록 응답"""
    app_id: str
    builds: List[JenkinsBuildLogItem]


class JenkinsBuildLogDetailResponse(BaseModel):
    """Jenkins 빌드 로그 상세 응답"""
    number: int
    logs: str
