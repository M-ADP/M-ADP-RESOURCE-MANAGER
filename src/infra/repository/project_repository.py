"""Project 도메인 Repository K8s 구현체"""

from typing import List, Optional

from kubernetes_asyncio.client import V1Namespace, V1ResourceQuota, V1Service

from src.core.project import ProjectRepository
from src.core.kubernetes.namespace import Namespace
from src.core.kubernetes.resource_quota import ResourceQuota
from src.core.kubernetes.service import Service, ServicePort
from src.infra.kubernetes.managers.namespace import NamespaceManager
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from src.infra.kubernetes.managers.service import ServiceManager


class K8sProjectRepository(ProjectRepository):
    """Project 도메인 Repository 구현체 (K8s)"""

    def __init__(
        self,
        namespace_manager: NamespaceManager,
        resource_quota_manager: ResourceQuotaManager,
        service_manager: ServiceManager,
    ):
        self._namespace_manager = namespace_manager
        self._resource_quota_manager = resource_quota_manager
        self._service_manager = service_manager

    # ── Namespace ────────────────────────────────────────────────────────────

    async def save_namespace(self, namespace: Namespace) -> Namespace:
        v1_ns = await self._namespace_manager.create_namespace(
            name=namespace.id,
            labels=namespace.labels or None,
            annotations=namespace.annotations or None,
        )
        return self._namespace_to_domain(v1_ns)

    async def find_namespace(self, id: str) -> Optional[Namespace]:
        v1_ns = await self._namespace_manager.get_namespace(id)
        if v1_ns is None:
            return None
        return self._namespace_to_domain(v1_ns)

    async def delete_namespace(self, id: str) -> bool:
        return await self._namespace_manager.delete_namespace(id)

    async def exists_namespace(self, id: str) -> bool:
        return await self._namespace_manager.exists(id)

    # ── ResourceQuota ────────────────────────────────────────────────────────

    async def save_resource_quota(self, resource_quota: ResourceQuota) -> ResourceQuota:
        v1_rq = await self._resource_quota_manager.create_resource_quota(
            name=resource_quota.id,
            namespace=resource_quota.namespace,
            hard_limits=resource_quota.hard_limits,
            labels=resource_quota.labels or None,
            annotations=resource_quota.annotations or None,
        )
        return self._resource_quota_to_domain(v1_rq)

    async def find_all_resource_quotas(
        self,
        namespace: str,
        label_selector: Optional[str] = None,
    ) -> List[ResourceQuota]:
        v1_rqs = await self._resource_quota_manager.list_resource_quotas(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._resource_quota_to_domain(rq) for rq in v1_rqs]

    async def exists_resource_quota(self, id: str, namespace: str) -> bool:
        return await self._resource_quota_manager.exists(id, namespace)

    async def delete_resource_quota(self, id: str, namespace: str) -> bool:
        return await self._resource_quota_manager.delete_resource_quota(id, namespace)

    # ── Service ──────────────────────────────────────────────────────────────

    async def find_service(self, id: str, namespace: str) -> Optional[Service]:
        v1_svc = await self._service_manager.get_service(id, namespace)
        if v1_svc is None:
            return None
        return self._service_to_domain(v1_svc)

    async def save_service(self, service: Service) -> Service:
        ports = [
            {
                "port": p.port,
                "targetPort": p.target_port,
                "protocol": p.protocol,
                "name": p.name,
                "nodePort": p.node_port,
            }
            for p in service.ports
        ]

        existing = await self._service_manager.get_service(service.id, service.namespace)
        if existing:
            v1_svc = await self._service_manager.update_service(
                name=service.id,
                namespace=service.namespace,
                ports=ports,
                selector=service.selector or None,
                service_type=service.service_type,
                labels=service.labels or None,
                annotations=service.annotations or None,
            )
        else:
            v1_svc = await self._service_manager.create_service(
                name=service.id,
                namespace=service.namespace,
                ports=ports,
                selector=service.selector or None,
                service_type=service.service_type,
                labels=service.labels or None,
                annotations=service.annotations or None,
            )
        return self._service_to_domain(v1_svc)

    async def delete_service(self, id: str, namespace: str) -> bool:
        return await self._service_manager.delete_service(id, namespace)

    # ── 변환 헬퍼 ────────────────────────────────────────────────────────────

    def _namespace_to_domain(self, v1_ns: V1Namespace) -> Namespace:
        labels = v1_ns.metadata.labels or {}
        return Namespace(
            id=v1_ns.metadata.name,
            name=labels.get("madp.io/name", ""),
            labels=labels,
            annotations=v1_ns.metadata.annotations or {},
            status=v1_ns.status.phase if v1_ns.status else None,
        )

    def _resource_quota_to_domain(self, v1_rq: V1ResourceQuota) -> ResourceQuota:
        labels = v1_rq.metadata.labels or {}
        return ResourceQuota(
            id=v1_rq.metadata.name,
            name=labels.get("madp.io/name", ""),
            namespace=v1_rq.metadata.namespace,
            hard_limits=v1_rq.spec.hard if v1_rq.spec and v1_rq.spec.hard else {},
            used=v1_rq.status.used if v1_rq.status and v1_rq.status.used else {},
            labels=labels,
            annotations=v1_rq.metadata.annotations or {},
        )

    def _service_to_domain(self, v1_svc: V1Service) -> Service:
        ports = []
        if v1_svc.spec and v1_svc.spec.ports:
            for p in v1_svc.spec.ports:
                ports.append(ServicePort(
                    port=p.port,
                    target_port=p.target_port if isinstance(p.target_port, int) else int(p.target_port),
                    protocol=p.protocol or "TCP",
                    name=p.name,
                    node_port=p.node_port,
                ))

        labels = v1_svc.metadata.labels or {}
        return Service(
            id=v1_svc.metadata.name,
            name=labels.get("madp.io/name", ""),
            namespace=v1_svc.metadata.namespace,
            ports=ports,
            selector=v1_svc.spec.selector if v1_svc.spec else {},
            service_type=v1_svc.spec.type if v1_svc.spec else "ClusterIP",
            labels=labels,
            annotations=v1_svc.metadata.annotations or {},
            cluster_ip=v1_svc.spec.cluster_ip if v1_svc.spec else None,
            external_ips=v1_svc.spec.external_ips if v1_svc.spec and v1_svc.spec.external_ips else [],
        )
