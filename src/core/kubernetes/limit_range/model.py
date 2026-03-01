from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class LimitRangeItem:
    """Kubernetes LimitRange Item"""

    type: str  # Pod, Container, PersistentVolumeClaim
    default: Optional[Dict[str, str]] = None
    default_request: Optional[Dict[str, str]] = None
    max: Optional[Dict[str, str]] = None
    min: Optional[Dict[str, str]] = None
    max_limit_request_ratio: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class LimitRange:
    """Kubernetes LimitRange 도메인 객체"""

    name: str
    namespace: str
    limits: List[LimitRangeItem] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def with_limit(self, limit: LimitRangeItem) -> "LimitRange":
        """새로운 리밋이 추가된 LimitRange 반환"""
        return LimitRange(
            name=self.name,
            namespace=self.namespace,
            limits=[*self.limits, limit],
            labels=self.labels,
            annotations=self.annotations,
        )

    def with_labels(self, labels: Dict[str, str]) -> "LimitRange":
        """새로운 레이블이 추가된 LimitRange 반환"""
        return LimitRange(
            name=self.name,
            namespace=self.namespace,
            limits=self.limits,
            labels={**self.labels, **labels},
            annotations=self.annotations,
        )
