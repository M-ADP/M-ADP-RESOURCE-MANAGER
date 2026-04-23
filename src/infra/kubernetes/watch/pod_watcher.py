import asyncio
from typing import Optional

from src.core.logger import Logger
from src.core.kubernetes.kubernetes_client import KubernetesClient
from .base_watcher import BaseWatcher
from .models import FailureRecord, FailureType


# containerStatus.state.waiting.reason → FailureType
# K8s Events에서 잡기 어려운 Pod 내부 상태 실패를 감지한다.
_WAITING_REASON_MAP: dict[str, FailureType] = {
    "ImagePullBackOff": FailureType.IMAGE_PULL_BACKOFF,
    "ErrImagePull": FailureType.IMAGE_PULL_BACKOFF,
    "CrashLoopBackOff": FailureType.CRASH_LOOP_BACKOFF,
}

# containerStatus.lastState.terminated.reason → FailureType
_TERMINATED_REASON_MAP: dict[str, FailureType] = {
    "OOMKilled": FailureType.OOM_KILLED,
}


class PodWatcher(BaseWatcher):
    """
    클러스터 전체 Pod 상태 변화를 구독해 ImagePullBackOff / OOMKilled / CrashLoopBackOff를 감지한다.

    이 실패들은 K8s Event reason에 나타나지 않거나 늦게 나타나기 때문에
    Pod status를 직접 관찰해야 한다.
    """

    def __init__(
        self,
        k8s_client: KubernetesClient,
        queue: asyncio.Queue,
        namespace_prefix: str,
        logger: Logger,
    ):
        super().__init__("pod-watcher", queue, namespace_prefix, logger)
        self._core_v1 = k8s_client.core_v1

    @property
    def _api_func(self):
        return self._core_v1.list_pod_for_all_namespaces

    async def _list_current(self):
        return await self._core_v1.list_pod_for_all_namespaces(limit=1)

    def _handle_event(self, event_type: str, obj) -> Optional[FailureRecord]:
        if event_type not in ("ADDED", "MODIFIED"):
            return None
        if obj is None or obj.status is None:
            return None

        namespace = obj.metadata.namespace
        if not self._is_target_namespace(namespace):
            return None

        labels = obj.metadata.labels or {}
        app_label = labels.get("app")

        for cs in obj.status.container_statuses or []:
            # 현재 waiting 상태 확인 (ImagePullBackOff, CrashLoopBackOff)
            if cs.state and cs.state.waiting:
                reason = cs.state.waiting.reason or ""
                failure_type = _WAITING_REASON_MAP.get(reason)
                if failure_type:
                    return FailureRecord(
                        namespace=namespace,
                        failure_type=failure_type,
                        reason=reason,
                        message=cs.state.waiting.message or "",
                        object_kind="Pod",
                        object_name=obj.metadata.name,
                        app_label=app_label,
                    )

            # 직전 종료 상태 확인 (OOMKilled)
            if cs.last_state and cs.last_state.terminated:
                reason = cs.last_state.terminated.reason or ""
                failure_type = _TERMINATED_REASON_MAP.get(reason)
                if failure_type:
                    return FailureRecord(
                        namespace=namespace,
                        failure_type=failure_type,
                        reason=reason,
                        message="",
                        object_kind="Pod",
                        object_name=obj.metadata.name,
                        app_label=app_label,
                    )

        return None
