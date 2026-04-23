from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.dependencies.watch import get_failure_store, get_watch_manager
from src.infra.kubernetes.watch.models import FailureType, WatcherState

watch_router = APIRouter(prefix="/watch", tags=["Watch"])


class WatcherStatusResponse(BaseModel):
    name: str
    is_running: bool
    restart_count: int
    last_event_at: Optional[datetime]
    last_error: Optional[str]


class WatchStatusResponse(BaseModel):
    is_running: bool
    event_watcher: WatcherStatusResponse
    pod_watcher: WatcherStatusResponse
    deployment_watcher: WatcherStatusResponse


class FailureRecordResponse(BaseModel):
    namespace: str
    failure_type: str
    reason: str
    message: str
    object_kind: str
    object_name: str
    app_label: Optional[str]
    detected_at: datetime


def _watcher_state_to_response(state: WatcherState) -> WatcherStatusResponse:
    return WatcherStatusResponse(
        name=state.name,
        is_running=state.is_running,
        restart_count=state.restart_count,
        last_event_at=state.last_event_at,
        last_error=state.last_error,
    )


_DISABLED_STATE = WatcherStatusResponse(
    name="",
    is_running=False,
    restart_count=0,
    last_event_at=None,
    last_error="watch disabled (K8S_WATCH_ENABLED=false)",
)


@watch_router.get("/status", response_model=WatchStatusResponse)
async def get_watch_status():
    """Watch 워커 생존 상태를 반환한다. 재시작 횟수와 마지막 오류를 포함한다."""
    manager = get_watch_manager()
    if manager is None:
        return WatchStatusResponse(
            is_running=False,
            event_watcher=_DISABLED_STATE,
            pod_watcher=_DISABLED_STATE,
            deployment_watcher=_DISABLED_STATE,
        )

    return WatchStatusResponse(
        is_running=manager.is_running,
        event_watcher=_watcher_state_to_response(manager.event_watcher_state),
        pod_watcher=_watcher_state_to_response(manager.pod_watcher_state),
        deployment_watcher=_watcher_state_to_response(manager.deployment_watcher_state),
    )


@watch_router.get("/failures", response_model=List[FailureRecordResponse])
async def get_failures(
    namespace: Optional[str] = Query(None, description="project-{id} 형식 네임스페이스"),
    failure_type: Optional[FailureType] = Query(None),
    since_seconds: Optional[int] = Query(None, ge=1, description="최근 N초 이내 실패만 반환"),
):
    """감지된 실패 목록을 최신 순으로 반환한다."""
    store = get_failure_store()
    records = store.query(
        namespace=namespace,
        failure_type=failure_type,
        since_seconds=since_seconds,
    )
    return [
        FailureRecordResponse(
            namespace=r.namespace,
            failure_type=r.failure_type,
            reason=r.reason,
            message=r.message,
            object_kind=r.object_kind,
            object_name=r.object_name,
            app_label=r.app_label,
            detected_at=r.detected_at,
        )
        for r in records
    ]
