from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core.kubernetes.deployment.model import Container


@dataclass(frozen=True)
class JobStatus:
    """Kubernetes Job 상태"""

    active: Optional[int] = None
    succeeded: Optional[int] = None
    failed: Optional[int] = None
    start_time: Optional[str] = None
    completion_time: Optional[str] = None


@dataclass(frozen=True)
class Job:
    """Kubernetes Job 도메인 객체"""

    name: str
    namespace: str
    containers: List[Container] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    backoff_limit: int = 6
    completions: int = 1
    parallelism: int = 1
    ttl_seconds_after_finished: Optional[int] = None
    restart_policy: str = "Never"
    status: Optional[JobStatus] = None

    def with_labels(self, labels: Dict[str, str]) -> "Job":
        """새로운 레이블이 추가된 Job 반환"""
        return Job(
            name=self.name,
            namespace=self.namespace,
            containers=self.containers,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            backoff_limit=self.backoff_limit,
            completions=self.completions,
            parallelism=self.parallelism,
            ttl_seconds_after_finished=self.ttl_seconds_after_finished,
            restart_policy=self.restart_policy,
            status=self.status,
        )
