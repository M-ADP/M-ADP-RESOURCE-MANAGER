"""Project 스키마"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """Project 생성 요청 모델"""

    name: str = Field(..., min_length=1)
    cpu: str = "100m" # 0.1v
    memory: str = "32Mi" # 32MB
    disk: str = "32Mi" # 32MB


class ProjectPortOpenRequest(BaseModel):
    """Project 포트 개방 요청 모델"""

    port: int = Field(..., gt=0, le=65535)
    protocol: str = "HTTP"