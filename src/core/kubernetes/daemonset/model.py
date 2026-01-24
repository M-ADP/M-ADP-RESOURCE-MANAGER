from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core.kubernetes.deployment.model import Container


@dataclass(frozen=True)
class DaemonSetStatus:
    """Kubernetes DaemonSet 상태"""

    current_number_scheduled: Optional[int] = None
    desired_number_scheduled: Optional[int] = None
    number_available: Optional[int] = None
    number_ready: Optional[int] = None


@dataclass(frozen=True)
class DaemonSet:
    """Kubernetes DaemonSet 도메인 객체"""

    name: str
    namespace: str
    containers: List[Container] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    selector_labels: Dict[str, str] = field(default_factory=dict)
    node_selector: Dict[str, str] = field(default_factory=dict)
    status: Optional[DaemonSetStatus] = None

    def with_labels(self, labels: Dict[str, str]) -> "DaemonSet":
        """새로운 레이블이 추가된 DaemonSet 반환"""
        return DaemonSet(
            name=self.name,
            namespace=self.namespace,
            containers=self.containers,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            node_selector=self.node_selector,
            status=self.status,
        )

    def with_node_selector(self, node_selector: Dict[str, str]) -> "DaemonSet":
        """NodeSelector가 변경된 DaemonSet 반환"""
        return DaemonSet(
            name=self.name,
            namespace=self.namespace,
            containers=self.containers,
            labels=self.labels,
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            node_selector={**self.node_selector, **node_selector},
            status=self.status,
        )
