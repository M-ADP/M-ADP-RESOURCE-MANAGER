from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.core.logger import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리"""
    logger.info("Application starting up...")

    from src.common.config.kubernetes import KubernetesConfig
    k8s_config = KubernetesConfig()

    if k8s_config.watch_enabled:
        from src.dependencies.kubernetes import get_kubernetes_client
        from src.dependencies.watch import get_failure_store, set_watch_manager
        from src.infra.kubernetes.watch.watch_manager import WatchManager
        from src.app.watch.failure_store import FailureStore

        k8s_client = await get_kubernetes_client()
        failure_store = FailureStore(ttl_seconds=k8s_config.watch_failure_ttl_seconds)
        watch_manager = WatchManager(
            k8s_client=k8s_client,
            failure_store=failure_store,
            namespace_prefix=k8s_config.watch_namespace_prefix,
            logger=logger,
        )
        set_watch_manager(watch_manager)
        await watch_manager.start()

    yield

    if k8s_config.watch_enabled:
        from src.dependencies.watch import get_watch_manager
        manager = get_watch_manager()
        if manager:
            await manager.stop()

    logger.info("Application shutting down...")
