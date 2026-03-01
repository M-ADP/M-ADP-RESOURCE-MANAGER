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
            "linstor-pv-fast.storageclass.storage.k8s.io/requests.storage": self.disk,
        }


@dataclass(frozen=True)
class ResourceQuota:
    """Kubernetes ResourceQuota 도메인 객체"""

    id: str
    name: str
    namespace: str
    hard_limits: Dict[str, str] = field(default_factory=dict)
    used: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_limits(
        cls,
        id: str,
        name: str,
        namespace: str,
        limits: ResourceQuotaLimits,
        labels: Optional[Dict[str, str]] = None,
    ) -> "ResourceQuota":
        """ResourceQuotaLimits로부터 ResourceQuota 생성"""
        return cls(
            id=id,
            name=name,
            namespace=namespace,
            hard_limits=limits.to_dict(),
            labels=labels or {},
        )

    @classmethod
    def for_project(
        cls,
        user_id: str,
        project_name: str,
        namespace: str,
        limits: ResourceQuotaLimits,
        labels: Optional[Dict[str, str]] = None,
    ) -> "ResourceQuota":
        """프로젝트의 ResourceQuota 생성 (이름 규칙 포함)"""
        quota_id = f"{namespace}-quota"
        return cls.from_limits(
            id=quota_id,
            name=project_name,
            namespace=namespace,
            limits=limits,
            labels={**(labels or {}), "madp.io/name": project_name},
        )

    def with_labels(self, labels: Dict[str, str]) -> "ResourceQuota":
        """새로운 레이블이 추가된 ResourceQuota 반환 (불변성 유지)"""
        return ResourceQuota(
            id=self.id,
            name=self.name,
            namespace=self.namespace,
            hard_limits=self.hard_limits,
            used=self.used,
            labels={**self.labels, **labels},
            annotations=self.annotations,
        )

    def with_cpu(self, cpu: str) -> "ResourceQuota":
        """CPU 제한이 변경된 ResourceQuota 반환"""
        new_limits = {
            **self.hard_limits,
            "requests.cpu": cpu,
            "limits.cpu": cpu,
        }
        return ResourceQuota(
            id=self.id, name=self.name, namespace=self.namespace,
            hard_limits=new_limits, used=self.used,
            labels=self.labels, annotations=self.annotations,
        )

    def with_memory(self, memory: str) -> "ResourceQuota":
        """메모리 제한이 변경된 ResourceQuota 반환"""
        new_limits = {
            **self.hard_limits,
            "requests.memory": memory,
            "limits.memory": memory,
        }
        return ResourceQuota(
            id=self.id, name=self.name, namespace=self.namespace,
            hard_limits=new_limits, used=self.used,
            labels=self.labels, annotations=self.annotations,
        )

    def with_disk(self, disk: str) -> "ResourceQuota":
        """디스크 제한이 변경된 ResourceQuota 반환"""
        new_limits = {
            **self.hard_limits,
            "requests.storage": disk,
            "linstor-pv-fast.storageclass.storage.k8s.io/requests.storage": disk,
        }
        return ResourceQuota(
            id=self.id, name=self.name, namespace=self.namespace,
            hard_limits=new_limits, used=self.used,
            labels=self.labels, annotations=self.annotations,
        )
