from pydantic import BaseModel
from typing import List


class PodLogInfo(BaseModel):
    """Pod 로그 정보"""
    pod_name: str
    logs: str


class AppLogsResponse(BaseModel):
    """App 로그 응답"""
    deployment_name: str
    namespace: str
    pod_logs: List[PodLogInfo]
