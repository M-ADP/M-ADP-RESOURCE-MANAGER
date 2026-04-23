import asyncio
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from kubernetes_asyncio import watch as k8s_watch
from kubernetes_asyncio.client.exceptions import ApiException

from src.core.logger import Logger
from .models import WatcherState, FailureRecord

_WATCH_TIMEOUT_SECONDS = 270   # 5분 미만 유지 → K8s API 서버 cache TTL 내 재연결
_BACKOFF_BASE = 2
_BACKOFF_MAX = 60
_BACKOFF_JITTER_RATIO = 0.3


class BaseWatcher(ABC):
    """
    K8s Watch 스트림을 위한 추상 기반 클래스.

    재연결 루프, resourceVersion 추적, 410 Gone 처리, 지수 백오프를 공통 제공한다.
    하위 클래스는 _api_func / _list_current / _handle_event 만 구현한다.
    """

    def __init__(self, name: str, queue: asyncio.Queue, namespace_prefix: str, logger: Logger):
        self.state = WatcherState(name=name)
        self._queue = queue
        self._namespace_prefix = namespace_prefix
        self._logger = logger
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._resource_version: str = ""

    def start(self) -> None:
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name=f"watcher-{self.state.name}")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.state.is_running = False

    async def _run(self) -> None:
        backoff = _BACKOFF_BASE
        self.state.is_running = True

        while not self._stop_event.is_set():
            w = None
            try:
                # resource_version이 없으면 현재 상태를 list해서 가져온다.
                # 이후 해당 시점 이후의 변경만 수신 → 과거 이벤트 재처리 방지.
                if not self._resource_version:
                    await self._init_resource_version()

                w = k8s_watch.Watch()
                self._logger.info(
                    f"[{self.state.name}] Watch 시작 (resourceVersion={self._resource_version})"
                )

                async for raw_event in w.stream(
                    self._api_func,
                    resource_version=self._resource_version,
                    timeout_seconds=_WATCH_TIMEOUT_SECONDS,
                    allow_watch_bookmarks=True,
                ):
                    if self._stop_event.is_set():
                        await w.stop()
                        return

                    event_type: str = raw_event.get("type", "")
                    # raw_object는 kubernetes-asyncio가 항상 dict로 보장한다.
                    # "object"는 역직렬화 실패 시 dict가 될 수 있어 신뢰할 수 없다.
                    raw_obj: dict = raw_event.get("raw_object") or {}

                    rv = raw_obj.get("metadata", {}).get("resourceVersion", "")
                    if event_type == "BOOKMARK":
                        if rv:
                            self._resource_version = rv
                        continue

                    if rv:
                        self._resource_version = rv
                        self.state.last_event_at = datetime.now(timezone.utc)

                    record = self._handle_event(event_type, raw_obj)
                    if record is not None:
                        try:
                            self._queue.put_nowait(record)
                        except asyncio.QueueFull:
                            self._logger.warning(
                                f"[{self.state.name}] 실패 큐 포화 상태, 이벤트 드롭"
                            )

                # 정상 timeout으로 스트림 종료 → 즉시 재연결 (backoff 불필요)
                backoff = _BACKOFF_BASE
                self._logger.info(f"[{self.state.name}] Watch 타임아웃, 재연결")

            except ApiException as e:
                if e.status == 410:
                    # 서버가 해당 resourceVersion을 GC → 재목록화로 최신 RV 획득
                    self._resource_version = ""
                    self._logger.warning(
                        f"[{self.state.name}] resourceVersion 만료(410 Gone), watch 초기화"
                    )
                    backoff = _BACKOFF_BASE
                else:
                    self._logger.error(
                        f"[{self.state.name}] K8s API 오류: status={e.status} reason={e.reason}"
                    )
                    self.state.last_error = f"ApiException {e.status}"
                    self.state.restart_count += 1
                    await self._sleep_with_backoff(backoff)
                    backoff = min(backoff * 2, _BACKOFF_MAX)

            except asyncio.CancelledError:
                if w:
                    await w.stop()
                self._logger.info(f"[{self.state.name}] Watch 종료")
                raise

            except Exception as e:
                self._logger.error(
                    f"[{self.state.name}] 예상치 못한 오류: {e}"
                )
                self.state.last_error = str(e)
                self.state.restart_count += 1
                await self._sleep_with_backoff(backoff)
                backoff = min(backoff * 2, _BACKOFF_MAX)

    async def _init_resource_version(self) -> None:
        """현재 리소스 목록에서 resourceVersion을 가져온다. limit=1로 트래픽 최소화."""
        result = await self._list_current()
        if isinstance(result, dict):
            self._resource_version = result.get("metadata", {}).get("resourceVersion", "")
        else:
            self._resource_version = result.metadata.resource_version
        self._logger.info(
            f"[{self.state.name}] 초기 resourceVersion 확보: {self._resource_version}"
        )

    async def _sleep_with_backoff(self, base: float) -> None:
        jitter = random.uniform(0, base * _BACKOFF_JITTER_RATIO)
        delay = base + jitter
        self._logger.info(f"[{self.state.name}] {delay:.1f}초 후 재시도")
        try:
            await asyncio.wait_for(asyncio.shield(self._stop_event.wait()), timeout=delay)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

    def _is_target_namespace(self, namespace: str) -> bool:
        return namespace.startswith(self._namespace_prefix)

    @property
    @abstractmethod
    def _api_func(self):
        """watch.Watch().stream()에 넘길 K8s API 메서드"""
        ...

    @abstractmethod
    async def _list_current(self):
        """초기 resourceVersion 획득을 위한 list 호출 결과 반환"""
        ...

    @abstractmethod
    def _handle_event(self, event_type: str, obj: dict) -> Optional[FailureRecord]:
        """이벤트 처리. raw_object dict를 받아 실패 레코드를 반환하거나 None 반환."""
        ...
