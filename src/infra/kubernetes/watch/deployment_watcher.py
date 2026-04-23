import asyncio
from typing import Optional

from src.core.logger import Logger
from src.core.kubernetes.kubernetes_client import KubernetesClient
from .base_watcher import BaseWatcher
from .models import FailureRecord, FailureType


class DeploymentWatcher(BaseWatcher):
    """
    Deployment status.conditions를 직접 관찰해 롤아웃 지연을 감지한다.

    감지 조건:
        conditions[type=Progressing, status=False, reason=ProgressDeadlineExceeded]

    중복 알림 방지:
        stall 상태로 진입한 Deployment는 _stalled 셋에 기록한다.
        회복(Progressing=True)되면 셋에서 제거해 재진입 시 재감지한다.
    """

    def __init__(
        self,
        k8s_client: KubernetesClient,
        queue: asyncio.Queue,
        namespace_prefix: str,
        logger: Logger,
    ):
        super().__init__("deployment-watcher", queue, namespace_prefix, logger)
        self._apps_v1 = k8s_client.apps_v1
        self._stalled: set[str] = set()

    @property
    def _api_func(self):
        return self._apps_v1.list_deployment_for_all_namespaces

    async def _list_current(self):
        return await self._apps_v1.list_deployment_for_all_namespaces(limit=1)

    def _handle_event(self, event_type: str, obj: dict) -> Optional[FailureRecord]:
        metadata = obj.get("metadata") or {}
        namespace = metadata.get("namespace", "")
        name = metadata.get("name", "")
        key = f"{namespace}/{name}"

        if event_type == "DELETED":
            self._stalled.discard(key)
            return None

        if event_type not in ("ADDED", "MODIFIED"):
            return None

        if not self._is_target_namespace(namespace):
            return None

        is_stalled = self._is_progress_deadline_exceeded(obj)

        if is_stalled:
            if key in self._stalled:
                return None  # 이미 감지한 건 — 중복 알림 방지
            self._stalled.add(key)

            app_label = (metadata.get("labels") or {}).get("app")
            return FailureRecord(
                namespace=namespace,
                failure_type=FailureType.ROLLOUT_STALL,
                reason="ProgressDeadlineExceeded",
                message=f"Deployment '{name}'의 롤아웃이 progressDeadlineSeconds를 초과했습니다.",
                object_kind="Deployment",
                object_name=name,
                app_label=app_label,
            )

        # stall 회복 → 셋에서 제거해 재진입 시 재감지 가능
        self._stalled.discard(key)
        return None

    @staticmethod
    def _is_progress_deadline_exceeded(obj: dict) -> bool:
        conditions = (obj.get("status") or {}).get("conditions") or []
        for condition in conditions:
            if (
                condition.get("type") == "Progressing"
                and condition.get("status") == "False"
                and condition.get("reason") == "ProgressDeadlineExceeded"
            ):
                return True
        return False
