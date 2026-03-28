"""Cloud DB 응답 스키마"""

from pydantic import BaseModel, Field


class CloudDbQueryResponse(BaseModel):
    """Cloud DB 쿼리 실행 응답"""

    output: str = Field(..., description="쿼리 실행 결과 (stdout)")
    error: str = Field(default="", description="에러 출력 (stderr)")


from src.api.v1.app.schemas.response import (
    AppCreateResponse as CloudDbCreateResponse,
    AppDeleteResponse as CloudDbDeleteResponse,
    AppRevisionResponse as CloudDbRevisionResponse,
    ContainerInfo,
    ContainerResourceInfo,
    ContainerResourcesInfo,
    DeploymentStatusInfo,
    PvcInfo,
)

__all__ = [
    "CloudDbCreateResponse",
    "CloudDbDeleteResponse",
    "CloudDbRevisionResponse",
    "CloudDbQueryResponse",
    "ContainerInfo",
    "ContainerResourceInfo",
    "ContainerResourcesInfo",
    "DeploymentStatusInfo",
    "PvcInfo",
]
