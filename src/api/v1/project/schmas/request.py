"""Project 스키마"""

from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """Project 생성 요청 모델"""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    cpu: str = "100m"
    memory: str = "32Mi"
    disk: str = "32Mi"


class ProjectResourceUpdateRequest(BaseModel):
    """Project 리소스 할당량 수정 요청 모델"""

    cpu: Optional[str] = None
    memory: Optional[str] = None
    disk: Optional[str] = None
