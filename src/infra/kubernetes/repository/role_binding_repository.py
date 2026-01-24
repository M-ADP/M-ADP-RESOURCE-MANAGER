from typing import List, Optional

from kubernetes_asyncio.client import V1RoleBinding

from src.core.kubernetes.role_binding import RoleBinding, RoleRef, Subject, RoleBindingRepository
from src.infra.kubernetes.managers.rolebinding import RoleBindingManager


class K8sRoleBindingRepository(RoleBindingRepository):
    """Kubernetes RoleBinding Repository 구현체"""

    def __init__(self, manager: RoleBindingManager):
        self._manager = manager

    async def save(self, role_binding: RoleBinding) -> RoleBinding:
        subjects = [
            {
                "kind": s.kind,
                "name": s.name,
                "namespace": s.namespace,
                "apiGroup": s.api_group if s.kind != "ServiceAccount" else "",
            }
            for s in role_binding.subjects
        ]
        role_ref = {
            "kind": role_binding.role_ref.kind,
            "name": role_binding.role_ref.name,
            "apiGroup": role_binding.role_ref.api_group,
        }
        v1_rb = await self._manager.create_role_binding(
            name=role_binding.name,
            namespace=role_binding.namespace,
            role_ref=role_ref,
            subjects=subjects,
            labels=role_binding.labels if role_binding.labels else None,
            annotations=role_binding.annotations if role_binding.annotations else None,
        )
        return self._to_domain(v1_rb)

    async def find_by_name(self, name: str, namespace: str) -> Optional[RoleBinding]:
        v1_rb = await self._manager.get_role_binding(name, namespace)
        if v1_rb is None:
            return None
        return self._to_domain(v1_rb)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[RoleBinding]:
        v1_rbs = await self._manager.list_role_bindings(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(rb) for rb in v1_rbs]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_role_binding(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    def _to_domain(self, v1_rb: V1RoleBinding) -> RoleBinding:
        subjects = []
        if v1_rb.subjects:
            for s in v1_rb.subjects:
                subjects.append(Subject(
                    kind=s.kind,
                    name=s.name,
                    namespace=s.namespace,
                    api_group=s.api_group or "rbac.authorization.k8s.io",
                ))

        role_ref = RoleRef(
            kind=v1_rb.role_ref.kind,
            name=v1_rb.role_ref.name,
            api_group=v1_rb.role_ref.api_group,
        )

        return RoleBinding(
            name=v1_rb.metadata.name,
            namespace=v1_rb.metadata.namespace,
            role_ref=role_ref,
            subjects=subjects,
            labels=v1_rb.metadata.labels or {},
            annotations=v1_rb.metadata.annotations or {},
        )
