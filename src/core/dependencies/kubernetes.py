from typing import Optional

from src.core.config.kubernetes import KubernetesConfig
from src.core.kubernetes.gateway import GatewayRepository
from src.core.kubernetes.namespace import NamespaceRepository
from src.core.kubernetes.resource_quota import ResourceQuotaRepository
from src.core.kubernetes.service import ServiceRepository
from src.core.logger import Logger
from src.infra.kubernetes import KubernetesClientImpl
from src.infra.kubernetes.managers.gateway.manager import IstioGatewayManager
from src.infra.kubernetes.managers.namespace import NamespaceManager
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from src.infra.kubernetes.managers.service import ServiceManager
from src.infra.kubernetes.repository.gateway_repository import K8sGatewayRepository
from src.infra.kubernetes.repository import K8sNamespaceRepository, K8sResourceQuotaRepository
from src.infra.kubernetes.repository.service_repository import K8sServiceRepository


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


async def get_resource_quota_repository() -> ResourceQuotaRepository:
    """ResourceQuotaRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = ResourceQuotaManager(k8s_client)
    return K8sResourceQuotaRepository(manager)


async def get_gateway_repository() -> GatewayRepository:
    """GatewayRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = IstioGatewayManager(k8s_client)
    return K8sGatewayRepository(manager)


async def get_service_repository() -> ServiceRepository:
    """ServiceRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = ServiceManager(k8s_client)
    return K8sServiceRepository(manager)
