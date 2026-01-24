from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Container:
    """Kubernetes Container 정의"""

    name: str
    image: str
    ports: List[Dict[str, Any]] = field(default_factory=list)
    env: List[Dict[str, Any]] = field(default_factory=list)
    resources: Optional[Dict[str, Any]] = None
    volume_mounts: List[Dict[str, Any]] = field(default_factory=list)
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None


@dataclass(frozen=True)
class DeploymentStatus:
    """Kubernetes Deployment 상태"""

    replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    available_replicas: Optional[int] = None
    updated_replicas: Optional[int] = None


@dataclass(frozen=True)
class Deployment:
    """Kubernetes Deployment 도메인 객체"""

    name: str
    namespace: str
    replicas: int = 1
    containers: List[Container] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    selector_labels: Dict[str, str] = field(default_factory=dict)
    status: Optional[DeploymentStatus] = None

    def with_replicas(self, replicas: int) -> "Deployment":
        """레플리카 수가 변경된 Deployment 반환"""
        return Deployment(
            name=self.name,
            namespace=self.namespace,
            replicas=replicas,
            containers=self.containers,
            labels=self.labels,
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            status=self.status,
        )

    def with_labels(self, labels: Dict[str, str]) -> "Deployment":
        """새로운 레이블이 추가된 Deployment 반환"""
        return Deployment(
            name=self.name,
            namespace=self.namespace,
            replicas=self.replicas,
            containers=self.containers,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            status=self.status,
        )
