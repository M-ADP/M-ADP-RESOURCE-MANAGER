from typing import List, Optional

from kubernetes_asyncio.client import V1Service

from src.core.kubernetes.service import Service, ServicePort, ServiceRepository
from src.infra.kubernetes.managers.service import ServiceManager


class K8sServiceRepository(ServiceRepository):
    """Kubernetes Service Repository 구현체"""

    def __init__(self, manager: ServiceManager):
        self._manager = manager

    async def save(self, service: Service) -> Service:
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
        v1_svc = await self._manager.create_service(
            name=service.id,
            namespace=service.namespace,
            ports=ports,
            selector=service.selector if service.selector else None,
            service_type=service.service_type,
            labels=service.labels if service.labels else None,
            annotations=service.annotations if service.annotations else None,
        )
        return self._to_domain(v1_svc)

    async def find_by_id(self, id: str, namespace: str) -> Optional[Service]:
        v1_svc = await self._manager.get_service(id, namespace)
        if v1_svc is None:
            return None
        return self._to_domain(v1_svc)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Service]:
        v1_svcs = await self._manager.list_services(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(svc) for svc in v1_svcs]

    async def delete(self, id: str, namespace: str) -> bool:
        return await self._manager.delete_service(id, namespace)

    async def exists(self, id: str, namespace: str) -> bool:
        return await self._manager.exists(id, namespace)

    def _to_domain(self, v1_svc: V1Service) -> Service:
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
