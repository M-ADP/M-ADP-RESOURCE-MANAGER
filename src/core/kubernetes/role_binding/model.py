from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Subject:
    """Kubernetes RoleBinding Subject"""

    kind: str  # User, Group, ServiceAccount
    name: str
    namespace: Optional[str] = None
    api_group: str = "rbac.authorization.k8s.io"


@dataclass(frozen=True)
class RoleRef:
    """Kubernetes RoleBinding RoleRef"""

    kind: str  # Role or ClusterRole
    name: str
    api_group: str = "rbac.authorization.k8s.io"


@dataclass(frozen=True)
class RoleBinding:
    """Kubernetes RoleBinding 도메인 객체"""

    name: str
    namespace: str
    role_ref: RoleRef
    subjects: List[Subject] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def with_subject(self, subject: Subject) -> "RoleBinding":
        """새로운 Subject가 추가된 RoleBinding 반환"""
        return RoleBinding(
            name=self.name,
            namespace=self.namespace,
            role_ref=self.role_ref,
            subjects=[*self.subjects, subject],
            labels=self.labels,
            annotations=self.annotations,
        )
