"""Kubernetes CronJob 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.cronjob.schema import (
    CronJobStatusInfo,
    CronJobInfo,
    CronJobListResponse,
    CronJobDetailResponse,
)
from src.infra.kubernetes.managers.cronjob import CronJobManager
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_cronjob_manager

cronjob_router = APIRouter(
    prefix="/cronjobs",
    tags=["kubernetes-cronjob"],
)


@cronjob_router.get("", response_model=SuccessResponse[CronJobListResponse])
async def list_cronjobs(
    namespace: Optional[str] = Query(default=None, description="Filter by namespace"),
    label_selector: Optional[str] = Query(default=None, description="Label selector"),
    cj_manager: CronJobManager = Depends(get_cronjob_manager),
):
    """Kubernetes CronJob 목록 조회"""
    cronjobs = await cj_manager.list_cronjobs(
        namespace=namespace,
        label_selector=label_selector,
    )

    cj_infos = [
        CronJobInfo(
            name=cj.metadata.name,
            namespace=cj.metadata.namespace,
            schedule=cj.spec.schedule if cj.spec else None,
            suspend=cj.spec.suspend if cj.spec else False,
            labels=cj.metadata.labels or {},
            annotations=cj.metadata.annotations or {},
            status=CronJobStatusInfo(
                last_schedule_time=str(cj.status.last_schedule_time) if cj.status and cj.status.last_schedule_time else None,
                last_successful_time=str(cj.status.last_successful_time) if cj.status and cj.status.last_successful_time else None,
                active_count=len(cj.status.active) if cj.status and cj.status.active else 0,
            ) if cj.status else None,
        )
        for cj in cronjobs
    ]

    return SuccessResponse(
        message="CronJobs retrieved successfully",
        data=CronJobListResponse(cronjobs=cj_infos, total=len(cj_infos)),
    )


@cronjob_router.get("/{namespace}/{name}", response_model=SuccessResponse[CronJobDetailResponse])
async def get_cronjob(
    namespace: str,
    name: str,
    cj_manager: CronJobManager = Depends(get_cronjob_manager),
):
    """특정 CronJob 상세 조회"""
    cj = await cj_manager.get_cronjob(name, namespace)

    if cj is None:
        raise HTTPException(status_code=404, detail=f"CronJob '{name}' not found in namespace '{namespace}'")

    cj_info = CronJobInfo(
        name=cj.metadata.name,
        namespace=cj.metadata.namespace,
        schedule=cj.spec.schedule if cj.spec else None,
        suspend=cj.spec.suspend if cj.spec else False,
        labels=cj.metadata.labels or {},
        annotations=cj.metadata.annotations or {},
        status=CronJobStatusInfo(
            last_schedule_time=str(cj.status.last_schedule_time) if cj.status and cj.status.last_schedule_time else None,
            last_successful_time=str(cj.status.last_successful_time) if cj.status and cj.status.last_successful_time else None,
            active_count=len(cj.status.active) if cj.status and cj.status.active else 0,
        ) if cj.status else None,
    )

    return SuccessResponse(
        message="CronJob retrieved successfully",
        data=CronJobDetailResponse(cronjob=cj_info),
    )
