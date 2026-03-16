from typing import Optional

from src.common.config.kubernetes import KubernetesConfig
from src.core.app_deployment import AppDeploymentRepository
from src.core.cloud_db import CloudDbRepository
from src.core.project import ProjectRepository
from src.core.logger import Logger
from src.infra.kubernetes import KubernetesClientImpl
from src.infra.kubernetes.managers.gateway import IstioGatewayManager
from src.infra.kubernetes.managers.virtualservice import IstioVirtualServiceManager
from src.infra.kubernetes.managers.namespace import NamespaceManager
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from src.infra.kubernetes.managers.service import ServiceManager
from src.infra.kubernetes.managers.vpa import VpaManager
from src.infra.kubernetes.managers.hpa import HpaManager
from src.infra.kubernetes.managers.limitrange import LimitRangeManager
from src.infra.kubernetes.managers.deployment import DeploymentManager
from src.infra.kubernetes.managers.service_account import ServiceAccountManager
from src.infra.kubernetes.managers.pod import PodManager
from src.infra.kubernetes.managers.configmap import ConfigMapManager
from src.infra.kubernetes.managers.statefulset import StatefulSetManager
from src.infra.kubernetes.managers.job import JobManager
from src.infra.kubernetes.managers.cronjob import CronJobManager
from src.infra.kubernetes.managers.persistentvolumeclaim import PersistentVolumeClaimManager
from src.infra.kubernetes.managers.rolebinding import RoleBindingManager
from src.infra.kubernetes.managers.node import NodeManager
from src.infra.kubernetes.managers.storage_class import StorageClassManager
from src.infra.repository import K8sAppDeploymentRepository, K8sCloudDbRepository, K8sProjectRepository


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


async def get_namespace_manager() -> NamespaceManager:
    """NamespaceManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return NamespaceManager(k8s_client)


async def get_resource_quota_manager() -> ResourceQuotaManager:
    """ResourceQuotaManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return ResourceQuotaManager(k8s_client)


async def get_gateway_manager() -> IstioGatewayManager:
    """IstioGatewayManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return IstioGatewayManager(k8s_client)


async def get_virtualservice_manager() -> IstioVirtualServiceManager:
    """IstioVirtualServiceManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return IstioVirtualServiceManager(k8s_client)


async def get_service_manager() -> ServiceManager:
    """ServiceManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return ServiceManager(k8s_client)


async def get_vpa_manager() -> VpaManager:
    """VpaManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return VpaManager(k8s_client)


async def get_limit_range_manager() -> LimitRangeManager:
    """LimitRangeManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return LimitRangeManager(k8s_client)


async def get_service_account_manager() -> ServiceAccountManager:
    """ServiceAccountManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return ServiceAccountManager(k8s_client)


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


async def get_hpa_manager() -> HpaManager:
    """HpaManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return HpaManager(k8s_client)


async def get_node_manager() -> NodeManager:
    """NodeManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return NodeManager(k8s_client)


async def get_storage_class_manager() -> StorageClassManager:
    """StorageClassManager 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return StorageClassManager(k8s_client)


# ── 도메인 Repository 팩토리 ─────────────────────────────────────────────────


async def get_app_deployment_repository() -> AppDeploymentRepository:
    """AppDeploymentRepository 인스턴스 반환"""
    from src.dependencies.vault import get_vault_client

    k8s_client = await get_kubernetes_client()
    vault_client = get_vault_client()
    return K8sAppDeploymentRepository(
        deployment_manager=DeploymentManager(k8s_client),
        pvc_manager=PersistentVolumeClaimManager(k8s_client),
        service_account_manager=ServiceAccountManager(k8s_client),
        hpa_manager=HpaManager(k8s_client),
        pod_manager=PodManager(k8s_client),
        configmap_manager=ConfigMapManager(k8s_client),
        vault_client=vault_client,
    )


async def get_cloud_db_repository() -> CloudDbRepository:
    """CloudDbRepository 인스턴스 반환"""
    from src.dependencies.vault import get_vault_client

    k8s_client = await get_kubernetes_client()
    vault_client = get_vault_client()
    return K8sCloudDbRepository(
        statefulset_manager=StatefulSetManager(k8s_client),
        pvc_manager=PersistentVolumeClaimManager(k8s_client),
        service_account_manager=ServiceAccountManager(k8s_client),
        hpa_manager=HpaManager(k8s_client),
        pod_manager=PodManager(k8s_client),
        configmap_manager=ConfigMapManager(k8s_client),
        vault_client=vault_client,
    )


async def get_project_repository() -> ProjectRepository:
    """ProjectRepository 인스턴스 반환"""
    k8s_client = await get_kubernetes_client()
    return K8sProjectRepository(
        namespace_manager=NamespaceManager(k8s_client),
        resource_quota_manager=ResourceQuotaManager(k8s_client),
        service_manager=ServiceManager(k8s_client),
        service_account_manager=ServiceAccountManager(k8s_client),
        rolebinding_manager=RoleBindingManager(k8s_client),
    )
