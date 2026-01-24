from typing import List, Optional

from kubernetes_asyncio.client import V1Role

from src.core.kubernetes.role import Role, PolicyRule, RoleRepository
from src.infra.kubernetes.managers.role import RoleManager


class K8sRoleRepository(RoleRepository):
    """Kubernetes Role Repository 구현체"""

    def __init__(self, manager: RoleManager):
        self._manager = manager

    async def save(self, role: Role) -> Role:
        rules = [
            {
                "apiGroups": rule.api_groups,
                "resources": rule.resources,
                "verbs": rule.verbs,
                "resourceNames": rule.resource_names if rule.resource_names else None,
            }
            for rule in role.rules
        ]
        v1_role = await self._manager.create_role(
            name=role.name,
            namespace=role.namespace,
            rules=rules,
            labels=role.labels if role.labels else None,
            annotations=role.annotations if role.annotations else None,
        )
        return self._to_domain(v1_role)

    async def find_by_name(self, name: str, namespace: str) -> Optional[Role]:
        v1_role = await self._manager.get_role(name, namespace)
        if v1_role is None:
            return None
        return self._to_domain(v1_role)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Role]:
        v1_roles = await self._manager.list_roles(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(r) for r in v1_roles]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_role(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_role: V1Role) -> Role:
        rules = []
        if v1_role.rules:
            for r in v1_role.rules:
                rules.append(PolicyRule(
                    api_groups=r.api_groups or [],
                    resources=r.resources or [],
                    verbs=r.verbs or [],
                    resource_names=r.resource_names or [],
                ))

        return Role(
            name=v1_role.metadata.name,
            namespace=v1_role.metadata.namespace,
            rules=rules,
            labels=v1_role.metadata.labels or {},
            annotations=v1_role.metadata.annotations or {},
        )
