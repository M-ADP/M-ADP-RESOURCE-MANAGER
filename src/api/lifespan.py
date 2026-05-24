from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.core.logger import get_logger

logger = get_logger()


def _validate_resource_defaults() -> None:
    """앱 기본 자원 제한이 프로젝트 자원 제한을 초과하지 않는지 검증"""
    from src.common.config.app_deployment import AppDeploymentConfig
    from src.common.config.project import ProjectConfig
    from src.common.util.unit_converter import UnitConverter

    app_cfg = AppDeploymentConfig()
    proj_cfg = ProjectConfig()

    app_memory = UnitConverter.parse_storage_to_bytes(app_cfg.default_memory_limit)
    proj_memory = UnitConverter.parse_storage_to_bytes(proj_cfg.default_memory)
    if app_memory > proj_memory:
        raise ValueError(
            f"APP_DEFAULT_MEMORY_LIMIT({app_cfg.default_memory_limit}) "
            f"이 PROJECT_DEFAULT_MEMORY({proj_cfg.default_memory})를 초과합니다."
        )

    app_cpu = UnitConverter.parse_cpu_to_millicores(app_cfg.default_cpu_limit)
    proj_cpu = UnitConverter.parse_cpu_to_millicores(proj_cfg.default_cpu)
    if app_cpu > proj_cpu:
        raise ValueError(
            f"APP_DEFAULT_CPU_LIMIT({app_cfg.default_cpu_limit}) "
            f"이 PROJECT_DEFAULT_CPU({proj_cfg.default_cpu})를 초과합니다."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리"""
    logger.info("Application starting up...")
    _validate_resource_defaults()

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
