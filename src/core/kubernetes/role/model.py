from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class PolicyRule:
    """Kubernetes Role PolicyRule"""

    api_groups: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    verbs: List[str] = field(default_factory=list)
    resource_names: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Role:
    """Kubernetes Role 도메인 객체"""

    name: str
    namespace: str
    rules: List[PolicyRule] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def with_rule(self, rule: PolicyRule) -> "Role":
        """새로운 규칙이 추가된 Role 반환"""
        return Role(
            name=self.name,
            namespace=self.namespace,
            rules=[*self.rules, rule],
            labels=self.labels,
            annotations=self.annotations,
        )
