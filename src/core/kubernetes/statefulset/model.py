from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.kubernetes.deployment.model import Container


@dataclass(frozen=True)
class StatefulSetStatus:
    """Kubernetes StatefulSet 상태"""

    replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    current_replicas: Optional[int] = None
    updated_replicas: Optional[int] = None


@dataclass(frozen=True)
class StatefulSet:
    """Kubernetes StatefulSet 도메인 객체"""

    name: str
    namespace: str
    service_name: str
    replicas: int = 1
    containers: List[Container] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    selector_labels: Dict[str, str] = field(default_factory=dict)
    volume_claim_templates: List[Dict[str, Any]] = field(default_factory=list)
    status: Optional[StatefulSetStatus] = None

    def with_replicas(self, replicas: int) -> "StatefulSet":
        """레플리카 수가 변경된 StatefulSet 반환"""
        return StatefulSet(
            name=self.name,
            namespace=self.namespace,
            service_name=self.service_name,
            replicas=replicas,
            containers=self.containers,
            labels=self.labels,
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            volume_claim_templates=self.volume_claim_templates,
            status=self.status,
        )

    def with_labels(self, labels: Dict[str, str]) -> "StatefulSet":
        """새로운 레이블이 추가된 StatefulSet 반환"""
        return StatefulSet(
            name=self.name,
            namespace=self.namespace,
            service_name=self.service_name,
            replicas=self.replicas,
            containers=self.containers,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            volume_claim_templates=self.volume_claim_templates,
            status=self.status,
        )
