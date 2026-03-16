"""Cloud DB 요청 스키마"""

from src.api.v1.app.schemas.request import (
    AppCreateRequest as CloudDbCreateRequest,
    AppRevisionRequest as CloudDbRevisionRequest,
)

__all__ = [
    "CloudDbCreateRequest",
    "CloudDbRevisionRequest",
]
