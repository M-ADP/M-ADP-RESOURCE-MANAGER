from typing import List, Optional

from kubernetes_asyncio.client import V1CronJob

from src.core.kubernetes.cronjob import CronJob, CronJobStatus, CronJobRepository
from src.core.kubernetes.deployment.model import Container
from src.infra.kubernetes.managers.cronjob import CronJobManager


class K8sCronJobRepository(CronJobRepository):
    """Kubernetes CronJob Repository 구현체"""

    def __init__(self, manager: CronJobManager):
        self._manager = manager

    async def save(self, cronjob: CronJob) -> CronJob:
        v1_cj = await self._manager.create_cronjob(
            name=cronjob.name,
            namespace=cronjob.namespace,
            schedule=cronjob.schedule,
            labels=cronjob.labels if cronjob.labels else None,
            annotations=cronjob.annotations if cronjob.annotations else None,
            suspend=cronjob.suspend,
            concurrency_policy=cronjob.concurrency_policy,
            successful_jobs_history_limit=cronjob.successful_jobs_history_limit,
            failed_jobs_history_limit=cronjob.failed_jobs_history_limit,
        )
        return self._to_domain(v1_cj)

    async def find_by_name(self, name: str, namespace: str) -> Optional[CronJob]:
        v1_cj = await self._manager.get_cronjob(name, namespace)
        if v1_cj is None:
            return None
        return self._to_domain(v1_cj)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[CronJob]:
        v1_cjs = await self._manager.list_cronjobs(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(cj) for cj in v1_cjs]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_cronjob(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_cj: V1CronJob) -> CronJob:
        containers = []
        if (v1_cj.spec and v1_cj.spec.job_template and 
            v1_cj.spec.job_template.spec and v1_cj.spec.job_template.spec.template and
            v1_cj.spec.job_template.spec.template.spec):
            for c in v1_cj.spec.job_template.spec.template.spec.containers or []:
                containers.append(Container(
                    name=c.name,
                    image=c.image,
                ))

        status = None
        if v1_cj.status:
            status = CronJobStatus(
                last_schedule_time=str(v1_cj.status.last_schedule_time) if v1_cj.status.last_schedule_time else None,
                last_successful_time=str(v1_cj.status.last_successful_time) if v1_cj.status.last_successful_time else None,
                active_jobs=len(v1_cj.status.active) if v1_cj.status.active else 0,
            )

        return CronJob(
            name=v1_cj.metadata.name,
            namespace=v1_cj.metadata.namespace,
            schedule=v1_cj.spec.schedule if v1_cj.spec else "",
            containers=containers,
            labels=v1_cj.metadata.labels or {},
            annotations=v1_cj.metadata.annotations or {},
            suspend=v1_cj.spec.suspend if v1_cj.spec else False,
            concurrency_policy=v1_cj.spec.concurrency_policy if v1_cj.spec else "Allow",
            status=status,
        )
