import asyncio
from typing import Optional

from src.core.logger import Logger
from src.core.kubernetes.kubernetes_client import KubernetesClient
from .event_watcher import EventWatcher
from .pod_watcher import PodWatcher
from .deployment_watcher import DeploymentWatcher
from .models import WatcherState, FailureRecord


class WatchManager:
    """
    EventWatcher + PodWatcher + DeploymentWatcher의 생명주기를 관리하고 헬스 상태를 노출한다.

    세 Watcher는 공유 asyncio.Queue에 FailureRecord를 push한다.
    consumer task가 큐를 드레인해 FailureStore에 저장하고 performops를 호출함으로써
    Watch I/O 루프와 실패 처리 로직을 분리한다.
    """

    def __init__(
        self,
        k8s_client: KubernetesClient,
        failure_store,
        namespace_prefix: str,
        logger: Logger,
        performops_client=None,
    ):
        self._failure_store = failure_store
        self._logger = logger
        self._performops_client = performops_client
        self._queue: asyncio.Queue[FailureRecord] = asyncio.Queue(maxsize=1000)
        self._consumer_task: Optional[asyncio.Task] = None

        self._event_watcher = EventWatcher(k8s_client, self._queue, namespace_prefix, logger)
        self._pod_watcher = PodWatcher(k8s_client, self._queue, namespace_prefix, logger)
        self._deployment_watcher = DeploymentWatcher(k8s_client, self._queue, namespace_prefix, logger)

    async def start(self) -> None:
        self._event_watcher.start()
        self._pod_watcher.start()
        self._deployment_watcher.start()
        self._consumer_task = asyncio.create_task(self._consume(), name="watch-consumer")
        self._logger.info("WatchManager 시작 완료")

    async def stop(self) -> None:
        await self._event_watcher.stop()
        await self._pod_watcher.stop()
        await self._deployment_watcher.stop()
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        self._logger.info("WatchManager 종료 완료")

    async def _consume(self) -> None:
        """큐를 드레인해 FailureStore에 저장하고 performops를 호출한다."""
        while True:
            try:
                record = await self._queue.get()
                self._failure_store.add(record)
                self._logger.info(
                    f"[watch] 실패 감지 namespace={record.namespace} "
                    f"type={record.failure_type} object={record.object_name}"
                )
                if self._performops_client is not None:
                    await self._performops_client.notify(record)
                self._queue.task_done()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._logger.error(f"[watch] consumer 오류: {e}")

    @property
    def event_watcher_state(self) -> WatcherState:
        return self._event_watcher.state

    @property
    def pod_watcher_state(self) -> WatcherState:
        return self._pod_watcher.state

    @property
    def deployment_watcher_state(self) -> WatcherState:
        return self._deployment_watcher.state

    @property
    def is_running(self) -> bool:
        return (
            self._event_watcher.state.is_running
            and self._pod_watcher.state.is_running
            and self._deployment_watcher.state.is_running
        )
