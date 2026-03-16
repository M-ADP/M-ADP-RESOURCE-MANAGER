from typing import Dict

from pydantic import BaseModel


class ProjectCreateResponse(BaseModel):
    """Project 생성 응답 모델"""

    namespace_id: str
    name: str
    resource_quota_id: str
    limits: Dict[str, str]


class ProjectDeleteResponse(BaseModel):
    """Project 삭제 응답 모델"""

    namespace_id: str
    resource_quota_deleted: bool


class ProjectResourceUpdateResponse(BaseModel):
    """Project 리소스 할당량 수정 응답 모델"""

    resource_quota: Dict[str, str]
