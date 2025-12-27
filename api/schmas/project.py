"""Project 스키마"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """Project 생성 요청 모델"""

    name: str = Field(..., min_length=1)
    cpu: str = "100m" # 0.1v
    memory: str = "32Mi" # 32MB
    disk: str = "32Mi" # 32MB


class ProjectCreateResponse(BaseModel):
    """Project 생성 응답 모델"""

    namespace: str
    resource_quota: str
    limits: Dict[str, str]
