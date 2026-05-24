"""Project 스키마"""

from typing import Optional

from pydantic import BaseModel, Field

from src.common.config.project import ProjectConfig

_config = ProjectConfig()


class ProjectCreateRequest(BaseModel):
    """Project 생성 요청 모델"""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    cpu: str = _config.default_cpu
    memory: str = _config.default_memory
    disk: str = _config.default_disk


class ProjectResourceUpdateRequest(BaseModel):
    """Project 리소스 할당량 수정 요청 모델"""

    cpu: Optional[str] = None
    memory: Optional[str] = None
    disk: Optional[str] = None
