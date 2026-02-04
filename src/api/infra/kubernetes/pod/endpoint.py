"""Kubernetes Pod 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.pod.schema import (
    ContainerStateInfo,
    ContainerStatusInfo,
    PodConditionInfo,
    PodStatusInfo,
    PodInfo,
    PodListResponse,
    PodDetailResponse,
    PodLogsResponse,
)
from src.infra.kubernetes.managers.pod import PodManager
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_pod_manager

pod_router = APIRouter(
    prefix="/pods",
    tags=["kubernetes-pod"],
)


def _convert_container_state(state_dict: dict) -> ContainerStateInfo:
    """Container 상태 변환"""
    return ContainerStateInfo(
        state=state_dict.get("state", "Unknown"),
        started_at=str(state_dict.get("started_at")) if state_dict.get("started_at") else None,
        finished_at=str(state_dict.get("finished_at")) if state_dict.get("finished_at") else None,
        exit_code=state_dict.get("exit_code"),
        reason=state_dict.get("reason"),
        message=state_dict.get("message"),
    )


def _convert_pod_status(status_dict: dict) -> PodStatusInfo:
    """Pod 상태 변환"""
    conditions = [
        PodConditionInfo(
            type=c.get("type", ""),
            status=c.get("status", ""),
            reason=c.get("reason"),
            message=c.get("message"),
        )
        for c in status_dict.get("conditions", [])
    ]

    container_statuses = [
        ContainerStatusInfo(
            name=cs.get("name", ""),
            ready=cs.get("ready", False),
            restart_count=cs.get("restart_count", 0),
            image=cs.get("image", ""),
            state=_convert_container_state(cs.get("state", {})),
        )
        for cs in status_dict.get("container_statuses", [])
    ]

    return PodStatusInfo(
        phase=status_dict.get("phase"),
        pod_ip=status_dict.get("pod_ip"),
        host_ip=status_dict.get("host_ip"),
        start_time=str(status_dict.get("start_time")) if status_dict.get("start_time") else None,
        conditions=conditions,
        container_statuses=container_statuses,
    )


@pod_router.get("", response_model=SuccessResponse[PodListResponse])
async def list_pods(
    namespace: Optional[str] = Query(
        default=None,
        description="Filter by namespace (all namespaces if not specified)",
    ),
    label_selector: Optional[str] = Query(
        default=None,
        description="Label selector (e.g., 'app_deployment=myapp')",
    ),
    pod_manager: PodManager = Depends(get_pod_manager),
):
    """Kubernetes Pod 목록 조회"""
    pods = await pod_manager.list_pods(
        namespace=namespace,
        label_selector=label_selector,
    )

    pod_infos = []
    for pod in pods:
        status = None
        if pod.status:
            status_dict = await pod_manager.get_pod_status(
                pod.metadata.name,
                pod.metadata.namespace,
            )
            if status_dict:
                status = _convert_pod_status(status_dict)

        pod_infos.append(
            PodInfo(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace,
                labels=pod.metadata.labels or {},
                annotations=pod.metadata.annotations or {},
                status=status,
            )
        )

    return SuccessResponse(
        message="Pods retrieved successfully",
        data=PodListResponse(
            pods=pod_infos,
            total=len(pod_infos),
        ),
    )


@pod_router.get("/{namespace}/{name}", response_model=SuccessResponse[PodDetailResponse])
async def get_pod(
    namespace: str,
    name: str,
    pod_manager: PodManager = Depends(get_pod_manager),
):
    """특정 Pod 상세 조회"""
    pod = await pod_manager.get_pod(name, namespace)

    if pod is None:
        raise HTTPException(
            status_code=404,
            detail=f"Pod '{name}' not found in namespace '{namespace}'",
        )

    status = None
    status_dict = await pod_manager.get_pod_status(name, namespace)
    if status_dict:
        status = _convert_pod_status(status_dict)

    pod_info = PodInfo(
        name=pod.metadata.name,
        namespace=pod.metadata.namespace,
        labels=pod.metadata.labels or {},
        annotations=pod.metadata.annotations or {},
        status=status,
    )

    return SuccessResponse(
        message="Pod retrieved successfully",
        data=PodDetailResponse(pod=pod_info),
    )


@pod_router.get("/{namespace}/{name}/logs", response_model=SuccessResponse[PodLogsResponse])
async def get_pod_logs(
    namespace: str,
    name: str,
    container: Optional[str] = Query(
        default=None,
        description="Container name (first container if not specified)",
    ),
    tail_lines: Optional[int] = Query(
        default=100,
        description="Number of lines to show from the end of the logs",
    ),
    since_seconds: Optional[int] = Query(
        default=None,
        description="Only return logs newer than this many seconds",
    ),
    timestamps: bool = Query(
        default=False,
        description="Include timestamps in log output",
    ),
    pod_manager: PodManager = Depends(get_pod_manager),
):
    """Pod 로그 조회"""
    # Pod 존재 여부 확인
    pod = await pod_manager.get_pod(name, namespace)
    if pod is None:
        raise HTTPException(
            status_code=404,
            detail=f"Pod '{name}' not found in namespace '{namespace}'",
        )

    logs = await pod_manager.get_pod_logs(
        name=name,
        namespace=namespace,
        container=container,
        tail_lines=tail_lines,
        since_seconds=since_seconds,
        timestamps=timestamps,
    )

    return SuccessResponse(
        message="Pod logs retrieved successfully",
        data=PodLogsResponse(
            pod_name=name,
            namespace=namespace,
            container=container,
            logs=logs or "",
        ),
    )
