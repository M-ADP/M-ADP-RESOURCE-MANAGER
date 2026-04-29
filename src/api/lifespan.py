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

    performops_client = None
    if k8s_config.watch_enabled:
        from src.dependencies.kubernetes import get_kubernetes_client
        from src.dependencies.watch import get_failure_store, set_failure_store, set_watch_manager
        from src.infra.kubernetes.watch.watch_manager import WatchManager
        from src.app.watch.failure_store import FailureStore
        from src.infra.http.performops_client import PerformopsClient

        k8s_client = await get_kubernetes_client()
        set_failure_store(FailureStore(ttl_seconds=k8s_config.watch_failure_ttl_seconds))
        failure_store = get_failure_store()

        if k8s_config.watch_performops_url:
            performops_client = PerformopsClient(
                base_url=k8s_config.watch_performops_url,
                logger=logger,
            )
            await performops_client.start()

        watch_manager = WatchManager(
            k8s_client=k8s_client,
            failure_store=failure_store,
            namespace_prefix=k8s_config.watch_namespace_prefix,
            logger=logger,
            performops_client=performops_client,
        )
        set_watch_manager(watch_manager)
        await watch_manager.start()

    yield

    if k8s_config.watch_enabled:
        from src.dependencies.watch import get_watch_manager
        manager = get_watch_manager()
        if manager:
            await manager.stop()
        if performops_client:
            await performops_client.stop()

    logger.info("Application shutting down...")
