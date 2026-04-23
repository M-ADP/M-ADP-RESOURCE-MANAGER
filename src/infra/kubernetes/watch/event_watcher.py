import asyncio
from typing import Optional

from src.core.logger import Logger
from src.core.kubernetes.kubernetes_client import KubernetesClient
from .base_watcher import BaseWatcher
from .models import FailureRecord, FailureType


_FAILURE_REASON_MAP: dict[str, FailureType] = {
    "FailedCreate": FailureType.FAILED_CREATE,
    "FailedScheduling": FailureType.FAILED_CREATE,
    "ExceededQuota": FailureType.QUOTA_EXCEEDED,
}


class EventWatcher(BaseWatcher):
    """
    클러스터 전체 K8s Events 스트림을 구독해 FailedCreate / quota 초과 이벤트를 감지한다.
    """

    def __init__(
        self,
        k8s_client: KubernetesClient,
        queue: asyncio.Queue,
        namespace_prefix: str,
        logger: Logger,
    ):
        super().__init__("event-watcher", queue, namespace_prefix, logger)
        self._core_v1 = k8s_client.core_v1

    @property
    def _api_func(self):
        return self._core_v1.list_event_for_all_namespaces

    async def _list_current(self):
        return await self._core_v1.list_event_for_all_namespaces(limit=1)

    def _handle_event(self, event_type: str, obj: dict) -> Optional[FailureRecord]:
        if event_type not in ("ADDED", "MODIFIED"):
            return None

        namespace = obj.get("metadata", {}).get("namespace", "")
        if not self._is_target_namespace(namespace):
            return None

        if obj.get("type") != "Warning":
            return None

        reason = obj.get("reason", "")
        failure_type = _FAILURE_REASON_MAP.get(reason)
        if failure_type is None:
            return None

        involved = obj.get("involvedObject") or {}
        return FailureRecord(
            namespace=namespace,
            failure_type=failure_type,
            reason=reason,
            message=obj.get("message", ""),
            object_kind=involved.get("kind", "Unknown"),
            object_name=involved.get("name", ""),
        )
