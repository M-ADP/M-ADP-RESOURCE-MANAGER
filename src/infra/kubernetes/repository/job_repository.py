from typing import List, Optional

from kubernetes_asyncio.client import V1Job

from src.core.kubernetes.job import Job, JobStatus, JobRepository
from src.core.kubernetes.deployment import Container
from src.infra.kubernetes.managers.job import JobManager


class K8sJobRepository(JobRepository):
    """Kubernetes Job Repository 구현체"""

    def __init__(self, manager: JobManager):
        self._manager = manager

    async def save(self, job: Job) -> Job:
        v1_job = await self._manager.create_job(
            name=job.name,
            namespace=job.namespace,
            labels=job.labels if job.labels else None,
            annotations=job.annotations if job.annotations else None,
            backoff_limit=job.backoff_limit,
            completions=job.completions,
            parallelism=job.parallelism,
            ttl_seconds_after_finished=job.ttl_seconds_after_finished,
        )
        return self._to_domain(v1_job)

    async def find_by_name(self, name: str, namespace: str) -> Optional[Job]:
        v1_job = await self._manager.get_job(name, namespace)
        if v1_job is None:
            return None
        return self._to_domain(v1_job)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Job]:
        v1_jobs = await self._manager.list_jobs(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(j) for j in v1_jobs]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_job(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_job: V1Job) -> Job:
        containers = []
        if v1_job.spec and v1_job.spec.template and v1_job.spec.template.spec:
            for c in v1_job.spec.template.spec.containers or []:
                containers.append(Container(
                    name=c.name,
                    image=c.image,
                ))

        status = None
        if v1_job.status:
            status = JobStatus(
                active=v1_job.status.active,
                succeeded=v1_job.status.succeeded,
                failed=v1_job.status.failed,
                start_time=str(v1_job.status.start_time) if v1_job.status.start_time else None,
                completion_time=str(v1_job.status.completion_time) if v1_job.status.completion_time else None,
            )

        return Job(
            name=v1_job.metadata.name,
            namespace=v1_job.metadata.namespace,
            containers=containers,
            labels=v1_job.metadata.labels or {},
            annotations=v1_job.metadata.annotations or {},
            backoff_limit=v1_job.spec.backoff_limit if v1_job.spec else 6,
            completions=v1_job.spec.completions if v1_job.spec else 1,
            parallelism=v1_job.spec.parallelism if v1_job.spec else 1,
            status=status,
        )
