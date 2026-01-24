from typing import Optional

from src.core.config.kubernetes import KubernetesConfig
from src.core.kubernetes.namespace import NamespaceRepository
from src.core.logger import Logger
from src.infra.kubernetes import KubernetesClientImpl
from src.infra.kubernetes.managers.namespace import NamespaceManager
from src.infra.kubernetes.repository import K8sNamespaceRepository


_k8s_client_instance: Optional[KubernetesClientImpl] = None


async def get_kubernetes_client(
        k8s_config: Optional[KubernetesConfig] = None,
        logger: Optional[Logger] = None
) -> KubernetesClientImpl:
    """
    Kubernetes 클라이언트 인스턴스 반환 (비동기 의존성 주입용)

    Args:
        k8s_config: Kubernetes 설정
        logger: 로거 인스턴스

    Returns:
        KubernetesClient: 초기화된 Kubernetes 클라이언트
    """
    global _k8s_client_instance

    if _k8s_client_instance is None:
        from src.core.config.kubernetes import KubernetesConfig
        from src.core.logger import get_logger

        config = k8s_config or KubernetesConfig()
        log = logger or get_logger()
        _k8s_client_instance = KubernetesClientImpl(config, log)
        await _k8s_client_instance.initialize()

    return _k8s_client_instance


async def get_namespace_repository() -> NamespaceRepository:
    """NamespaceRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = NamespaceManager(k8s_client)
    return K8sNamespaceRepository(manager)
