from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class ResourceQuotaLimits:
    """ResourceQuota 하드 리밋 구성"""

    cpu: str
    memory: str
    disk: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "requests.cpu": self.cpu,
            "limits.cpu": self.cpu,
            "requests.memory": self.memory,
            "limits.memory": self.memory,
            "requests.storage": self.disk,
        }


@dataclass(frozen=True)
class ResourceQuota:
    """Kubernetes ResourceQuota 도메인 객체"""

    name: str
    namespace: str
    hard_limits: Dict[str, str] = field(default_factory=dict)
    used: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_limits(
        cls,
        name: str,
        namespace: str,
        limits: ResourceQuotaLimits,
        labels: Optional[Dict[str, str]] = None,
    ) -> "ResourceQuota":
        """ResourceQuotaLimits로부터 ResourceQuota 생성"""
        return cls(
            name=name,
            namespace=namespace,
            hard_limits=limits.to_dict(),
            labels=labels or {},
        )

    def with_labels(self, labels: Dict[str, str]) -> "ResourceQuota":
        """새로운 레이블이 추가된 ResourceQuota 반환 (불변성 유지)"""
        return ResourceQuota(
            name=self.name,
            namespace=self.namespace,
            hard_limits=self.hard_limits,
            used=self.used,
            labels={**self.labels, **labels},
            annotations=self.annotations,
        )
