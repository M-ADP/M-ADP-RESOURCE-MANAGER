from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core.kubernetes.deployment import Container


@dataclass(frozen=True)
class ReplicaSetStatus:
    """Kubernetes ReplicaSet 상태"""

    replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    available_replicas: Optional[int] = None


@dataclass(frozen=True)
class ReplicaSet:
    """Kubernetes ReplicaSet 도메인 객체"""

    name: str
    namespace: str
    replicas: int = 1
    containers: List[Container] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    selector_labels: Dict[str, str] = field(default_factory=dict)
    status: Optional[ReplicaSetStatus] = None

    def with_replicas(self, replicas: int) -> "ReplicaSet":
        """레플리카 수가 변경된 ReplicaSet 반환"""
        return ReplicaSet(
            name=self.name,
            namespace=self.namespace,
            replicas=replicas,
            containers=self.containers,
            labels=self.labels,
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            status=self.status,
        )

    def with_labels(self, labels: Dict[str, str]) -> "ReplicaSet":
        """새로운 레이블이 추가된 ReplicaSet 반환"""
        return ReplicaSet(
            name=self.name,
            namespace=self.namespace,
            replicas=self.replicas,
            containers=self.containers,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            status=self.status,
        )
