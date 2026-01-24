from typing import Dict

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
