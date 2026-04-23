from typing import Optional

from src.app.watch.failure_store import FailureStore

_watch_manager = None
_failure_store_instance: Optional[FailureStore] = None


def get_failure_store() -> FailureStore:
    global _failure_store_instance
    if _failure_store_instance is None:
        _failure_store_instance = FailureStore()
    return _failure_store_instance


def get_watch_manager():
    return _watch_manager


def set_watch_manager(manager) -> None:
    global _watch_manager
    _watch_manager = manager
