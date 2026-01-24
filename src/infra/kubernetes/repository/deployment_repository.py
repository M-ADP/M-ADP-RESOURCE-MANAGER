from typing import List, Optional

from kubernetes_asyncio.client import V1Deployment, V1Container

from src.core.kubernetes.deployment import Deployment, Container, DeploymentStatus, DeploymentRepository
from src.infra.kubernetes.managers.deployment import DeploymentManager


class K8sDeploymentRepository(DeploymentRepository):
    """Kubernetes Deployment Repository 구현체"""

    def __init__(self, manager: DeploymentManager):
        self._manager = manager

    async def save(self, deployment: Deployment) -> Deployment:
        containers = [
            V1Container(
                name=c.name,
                image=c.image,
                ports=c.ports if c.ports else None,
                env=c.env if c.env else None,
                resources=c.resources,
                volume_mounts=c.volume_mounts if c.volume_mounts else None,
                command=c.command,
                args=c.args,
            )
            for c in deployment.containers
        ]
        v1_dep = await self._manager.create_deployment(
            name=deployment.name,
            namespace=deployment.namespace,
            containers=containers,
            replicas=deployment.replicas,
            labels=deployment.labels if deployment.labels else None,
            annotations=deployment.annotations if deployment.annotations else None,
            selector_labels=deployment.selector_labels if deployment.selector_labels else None,
        )
        return self._to_domain(v1_dep)

    async def find_by_name(self, name: str, namespace: str) -> Optional[Deployment]:
        v1_dep = await self._manager.get_deployment(name, namespace)
        if v1_dep is None:
            return None
        return self._to_domain(v1_dep)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Deployment]:
        v1_deps = await self._manager.list_deployments(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(d) for d in v1_deps]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_deployment(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_dep: V1Deployment) -> Deployment:
        containers = []
        if v1_dep.spec and v1_dep.spec.template and v1_dep.spec.template.spec:
            for c in v1_dep.spec.template.spec.containers or []:
                containers.append(Container(
                    name=c.name,
                    image=c.image,
                ))

        status = None
        if v1_dep.status:
            status = DeploymentStatus(
                replicas=v1_dep.status.replicas,
                ready_replicas=v1_dep.status.ready_replicas,
                available_replicas=v1_dep.status.available_replicas,
                updated_replicas=v1_dep.status.updated_replicas,
            )

        return Deployment(
            name=v1_dep.metadata.name,
            namespace=v1_dep.metadata.namespace,
            replicas=v1_dep.spec.replicas if v1_dep.spec else 1,
            containers=containers,
            labels=v1_dep.metadata.labels or {},
            annotations=v1_dep.metadata.annotations or {},
            selector_labels=v1_dep.spec.selector.match_labels if v1_dep.spec and v1_dep.spec.selector else {},
            status=status,
        )
