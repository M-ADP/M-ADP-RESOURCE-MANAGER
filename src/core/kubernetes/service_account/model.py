from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ServiceAccount:
    """Kubernetes ServiceAccount 도메인 객체"""

    name: str
    namespace: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    image_pull_secrets: List[str] = field(default_factory=list)

    def with_labels(self, labels: Dict[str, str]) -> "ServiceAccount":
        """새로운 레이블이 추가된 ServiceAccount 반환"""
        return ServiceAccount(
            name=self.name,
            namespace=self.namespace,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            image_pull_secrets=self.image_pull_secrets,
        )

    def with_image_pull_secret(self, secret_name: str) -> "ServiceAccount":
        """ImagePullSecret이 추가된 ServiceAccount 반환"""
        return ServiceAccount(
            name=self.name,
            namespace=self.namespace,
            labels=self.labels,
            annotations=self.annotations,
            image_pull_secrets=[*self.image_pull_secrets, secret_name],
        )
