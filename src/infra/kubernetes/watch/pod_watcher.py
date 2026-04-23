import asyncio
from typing import Optional

from src.core.logger import Logger
from src.core.kubernetes.kubernetes_client import KubernetesClient
from .base_watcher import BaseWatcher
from .models import FailureRecord, FailureType


_WAITING_REASON_MAP: dict[str, FailureType] = {
    "ImagePullBackOff": FailureType.IMAGE_PULL_BACKOFF,
    "ErrImagePull": FailureType.IMAGE_PULL_BACKOFF,
    "CrashLoopBackOff": FailureType.CRASH_LOOP_BACKOFF,
}

_TERMINATED_REASON_MAP: dict[str, FailureType] = {
    "OOMKilled": FailureType.OOM_KILLED,
}


class PodWatcher(BaseWatcher):
    """
    클러스터 전체 Pod 상태 변화를 구독해 ImagePullBackOff / OOMKilled / CrashLoopBackOff를 감지한다.
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

    def _handle_event(self, event_type: str, obj: dict) -> Optional[FailureRecord]:
        if event_type not in ("ADDED", "MODIFIED"):
            return None

        metadata = obj.get("metadata") or {}
        namespace = metadata.get("namespace", "")
        if not self._is_target_namespace(namespace):
            return None

        pod_name = metadata.get("name", "")
        app_label = (metadata.get("labels") or {}).get("app")

        for cs in (obj.get("status") or {}).get("containerStatuses") or []:
            # 현재 waiting 상태 (ImagePullBackOff, CrashLoopBackOff)
            waiting = (cs.get("state") or {}).get("waiting") or {}
            reason = waiting.get("reason", "")
            failure_type = _WAITING_REASON_MAP.get(reason)
            if failure_type:
                return FailureRecord(
                    namespace=namespace,
                    failure_type=failure_type,
                    reason=reason,
                    message=waiting.get("message", ""),
                    object_kind="Pod",
                    object_name=pod_name,
                    app_label=app_label,
                )

            # 직전 종료 상태 (OOMKilled)
            terminated = (cs.get("lastState") or {}).get("terminated") or {}
            reason = terminated.get("reason", "")
            failure_type = _TERMINATED_REASON_MAP.get(reason)
            if failure_type:
                return FailureRecord(
                    namespace=namespace,
                    failure_type=failure_type,
                    reason=reason,
                    message="",
                    object_kind="Pod",
                    object_name=pod_name,
                    app_label=app_label,
                )

        return None
