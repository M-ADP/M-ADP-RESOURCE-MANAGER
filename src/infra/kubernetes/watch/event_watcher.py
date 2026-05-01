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

    중복 알림 방지:
        같은 K8s Event 오브젝트(UID 기준)가 count++ MODIFIED로 여러 번 수신되어도
        최초 ADDED 시점에만 FailureRecord를 발행한다.
        resourceVersion이 초기화(410 Gone, 재시작)되면 _seen_uids를 초기화해
        장기 실패가 재감지될 수 있도록 한다.
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
        self._seen_uids: set[str] = set()

    def _on_resource_version_reset(self) -> None:
        self._seen_uids.clear()

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

        uid = obj.get("metadata", {}).get("uid", "")
        if uid:
            if uid in self._seen_uids:
                return None
            self._seen_uids.add(uid)

        involved = obj.get("involvedObject") or {}
        return FailureRecord(
            namespace=namespace,
            failure_type=failure_type,
            reason=reason,
            message=obj.get("message", ""),
            object_kind=involved.get("kind", "Unknown"),
            object_name=involved.get("name", ""),
        )
