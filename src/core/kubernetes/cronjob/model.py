from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core.kubernetes.deployment.model import Container


@dataclass(frozen=True)
class CronJobStatus:
    """Kubernetes CronJob 상태"""

    last_schedule_time: Optional[str] = None
    last_successful_time: Optional[str] = None
    active_jobs: int = 0


@dataclass(frozen=True)
class CronJob:
    """Kubernetes CronJob 도메인 객체"""

    name: str
    namespace: str
    schedule: str  # Cron 표현식
    containers: List[Container] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    suspend: bool = False
    concurrency_policy: str = "Allow"  # Allow, Forbid, Replace
    successful_jobs_history_limit: int = 3
    failed_jobs_history_limit: int = 1
    restart_policy: str = "OnFailure"
    status: Optional[CronJobStatus] = None

    def with_schedule(self, schedule: str) -> "CronJob":
        """스케줄이 변경된 CronJob 반환"""
        return CronJob(
            name=self.name,
            namespace=self.namespace,
            schedule=schedule,
            containers=self.containers,
            labels=self.labels,
            annotations=self.annotations,
            suspend=self.suspend,
            concurrency_policy=self.concurrency_policy,
            successful_jobs_history_limit=self.successful_jobs_history_limit,
            failed_jobs_history_limit=self.failed_jobs_history_limit,
            restart_policy=self.restart_policy,
            status=self.status,
        )

    def with_suspend(self, suspend: bool) -> "CronJob":
        """일시중지 상태가 변경된 CronJob 반환"""
        return CronJob(
            name=self.name,
            namespace=self.namespace,
            schedule=self.schedule,
            containers=self.containers,
            labels=self.labels,
            annotations=self.annotations,
            suspend=suspend,
            concurrency_policy=self.concurrency_policy,
            successful_jobs_history_limit=self.successful_jobs_history_limit,
            failed_jobs_history_limit=self.failed_jobs_history_limit,
            restart_policy=self.restart_policy,
            status=self.status,
        )
