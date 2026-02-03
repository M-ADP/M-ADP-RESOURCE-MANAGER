from typing import Optional

from src.common.config.kubernetes import KubernetesConfig
from src.core.kubernetes.gateway import GatewayRepository
from src.core.kubernetes.namespace import NamespaceRepository
from src.core.kubernetes.resource_quota import ResourceQuotaRepository
from src.core.kubernetes.service import ServiceRepository
from src.core.kubernetes.vpa import VpaRepository
from src.core.kubernetes.hpa import HpaRepository
from src.core.kubernetes.limit_range import LimitRangeRepository
from src.core.kubernetes.deployment import DeploymentRepository
from src.core.kubernetes.persistent_volume_claim import PersistentVolumeClaimRepository
from src.core.kubernetes.pod import PodRepository
from src.core.logger import Logger
from src.infra.kubernetes import KubernetesClientImpl
from src.infra.kubernetes.managers.gateway import IstioGatewayManager
from src.infra.kubernetes.managers.namespace import NamespaceManager
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from src.infra.kubernetes.managers.service import ServiceManager
from src.infra.kubernetes.managers.vpa import VpaManager
from src.infra.kubernetes.managers.hpa import HpaManager
from src.infra.kubernetes.managers.limitrange import LimitRangeManager
from src.infra.kubernetes.managers.deployment import DeploymentManager
from src.infra.kubernetes.managers.pod import PodManager
from src.infra.kubernetes.managers.configmap import ConfigMapManager
from src.infra.kubernetes.managers.statefulset import StatefulSetManager
from src.infra.kubernetes.managers.job import JobManager
from src.infra.kubernetes.managers.cronjob import CronJobManager
from src.infra.kubernetes.managers.persistentvolumeclaim import PersistentVolumeClaimManager
from src.infra.kubernetes.repository import (
    K8sNamespaceRepository,
    K8sResourceQuotaRepository,
    K8sServiceRepository,
    K8sLimitRangeRepository,
    K8sDeploymentRepository,
    K8sGatewayRepository,
    K8sVpaRepository,
    K8sHpaRepository,
    K8sPersistentVolumeClaimRepository,
    K8sPodRepository,
)


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
        from src.common.config.kubernetes import KubernetesConfig
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


async def get_vpa_repository() -> VpaRepository:
    """VpaRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = VpaManager(k8s_client)
    return K8sVpaRepository(manager)


async def get_limit_range_repository() -> LimitRangeRepository:
    """LimitRangeRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = LimitRangeManager(k8s_client)
    return K8sLimitRangeRepository(manager)


async def get_deployment_repository() -> DeploymentRepository:
    """DeploymentRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = DeploymentManager(k8s_client)
    return K8sDeploymentRepository(manager)


async def get_deployment_manager() -> DeploymentManager:
    """DeploymentManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return DeploymentManager(k8s_client)


async def get_pod_manager() -> PodManager:
    """PodManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return PodManager(k8s_client)


async def get_configmap_manager() -> ConfigMapManager:
    """ConfigMapManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return ConfigMapManager(k8s_client)


async def get_statefulset_manager() -> StatefulSetManager:
    """StatefulSetManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return StatefulSetManager(k8s_client)


async def get_job_manager() -> JobManager:
    """JobManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return JobManager(k8s_client)


async def get_cronjob_manager() -> CronJobManager:
    """CronJobManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return CronJobManager(k8s_client)


async def get_pvc_manager() -> PersistentVolumeClaimManager:
    """PersistentVolumeClaimManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return PersistentVolumeClaimManager(k8s_client)


async def get_pvc_repository() -> PersistentVolumeClaimRepository:
    """PersistentVolumeClaimRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = PersistentVolumeClaimManager(k8s_client)
    return K8sPersistentVolumeClaimRepository(manager)


async def get_pod_repository() -> PodRepository:
    """PodRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = PodManager(k8s_client)
    return K8sPodRepository(manager)


async def get_hpa_repository() -> HpaRepository:
    """HpaRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    manager = HpaManager(k8s_client)
    return K8sHpaRepository(manager)
