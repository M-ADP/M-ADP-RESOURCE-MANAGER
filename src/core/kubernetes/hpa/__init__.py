"""HPA 도메인 모듈"""

from .model import (
    HorizontalPodAutoscaler,
    HpaMetricSpec,
    HpaScaleTargetRef,
    HpaStatus,
)
from .repository import HpaRepository

__all__ = [
    "HorizontalPodAutoscaler",
    "HpaMetricSpec",
    "HpaScaleTargetRef",
    "HpaStatus",
    "HpaRepository",
]
