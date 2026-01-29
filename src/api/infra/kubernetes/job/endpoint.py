"""Kubernetes Job 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.job.schema import (
    JobStatusInfo,
    JobInfo,
    JobListResponse,
    JobDetailResponse,
)
from src.infra.kubernetes.managers.job import JobManager
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_job_manager

job_router = APIRouter(
    prefix="/jobs",
    tags=["kubernetes-job"],
)


@job_router.get("", response_model=SuccessResponse[JobListResponse])
async def list_jobs(
    namespace: Optional[str] = Query(default=None, description="Filter by namespace"),
    label_selector: Optional[str] = Query(default=None, description="Label selector"),
    job_manager: JobManager = Depends(get_job_manager),
):
    """Kubernetes Job 목록 조회"""
    jobs = await job_manager.list_jobs(
        namespace=namespace,
        label_selector=label_selector,
    )

    job_infos = [
        JobInfo(
            name=job.metadata.name,
            namespace=job.metadata.namespace,
            completions=job.spec.completions if job.spec else None,
            parallelism=job.spec.parallelism if job.spec else None,
            labels=job.metadata.labels or {},
            annotations=job.metadata.annotations or {},
            status=JobStatusInfo(
                active=job.status.active,
                succeeded=job.status.succeeded,
                failed=job.status.failed,
                start_time=str(job.status.start_time) if job.status.start_time else None,
                completion_time=str(job.status.completion_time) if job.status.completion_time else None,
            ) if job.status else None,
        )
        for job in jobs
    ]

    return SuccessResponse(
        message="Jobs retrieved successfully",
        data=JobListResponse(jobs=job_infos, total=len(job_infos)),
    )


@job_router.get("/{namespace}/{name}", response_model=SuccessResponse[JobDetailResponse])
async def get_job(
    namespace: str,
    name: str,
    job_manager: JobManager = Depends(get_job_manager),
):
    """특정 Job 상세 조회"""
    job = await job_manager.get_job(name, namespace)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{name}' not found in namespace '{namespace}'")

    job_info = JobInfo(
        name=job.metadata.name,
        namespace=job.metadata.namespace,
        completions=job.spec.completions if job.spec else None,
        parallelism=job.spec.parallelism if job.spec else None,
        labels=job.metadata.labels or {},
        annotations=job.metadata.annotations or {},
        status=JobStatusInfo(
            active=job.status.active,
            succeeded=job.status.succeeded,
            failed=job.status.failed,
            start_time=str(job.status.start_time) if job.status.start_time else None,
            completion_time=str(job.status.completion_time) if job.status.completion_time else None,
        ) if job.status else None,
    )

    return SuccessResponse(
        message="Job retrieved successfully",
        data=JobDetailResponse(job=job_info),
    )
