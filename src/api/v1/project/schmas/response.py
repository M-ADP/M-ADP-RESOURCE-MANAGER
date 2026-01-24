from typing import Dict, List

from pydantic import BaseModel


class ProjectCreateResponse(BaseModel):
    """Project 생성 응답 모델"""

    namespace: str
    resource_quota: str
    limits: Dict[str, str]


class ProjectDeleteResponse(BaseModel):
    """Project 삭제 응답 모델"""

    namespace: str
    resource_quota_deleted: bool


class ProjectPortOpenResponse(BaseModel):
    """Project 포트 개방 응답 모델"""

    gateway_name: str
    namespace: str
    port: int
    protocol: str
    hosts: List[str]


class ProjectPortDeleteResponse(BaseModel):
    """Project 포트 삭제 응답 모델"""

    gateway_deleted: bool
