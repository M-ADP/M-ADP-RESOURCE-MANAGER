from typing import List, Optional, Dict, Any

from src.core.kubernetes.vpa import VerticalPodAutoscaler, VpaRepository, VpaTargetRef, VpaUpdatePolicy
from src.infra.kubernetes.managers.vpa.manager import VpaManager


class K8sVpaRepository(VpaRepository):
    """Kubernetes VPA Repository 구현체"""

    def __init__(self, manager: VpaManager):
        self._manager = manager

    async def save(self, vpa: VerticalPodAutoscaler) -> VerticalPodAutoscaler:
        """VPA 저장 (생성 또는 업데이트)"""
        body = self._to_k8s_body(vpa)
        raw_vpa = await self._manager.create_vpa(namespace=vpa.namespace, body=body)
        return self._to_domain(raw_vpa)

    async def find_by_name(self, name: str, namespace: str) -> Optional[VerticalPodAutoscaler]:
        """이름으로 VPA 조회"""
        raw_vpa = await self._manager.get_vpa(name, namespace)
        return self._to_domain(raw_vpa) if raw_vpa else None

    async def find_all(self, namespace: str) -> List[VerticalPodAutoscaler]:
        """네임스페이스 내의 모든 VPA 조회"""
        raw_vpas = await self._manager.list_vpas(namespace)
        return [self._to_domain(v) for v in raw_vpas]

    async def delete(self, name: str, namespace: str) -> bool:
        """VPA 삭제"""
        return await self._manager.delete_vpa(name, namespace)

    def _to_k8s_body(self, vpa: VerticalPodAutoscaler) -> Dict[str, Any]:
        """도메인 객체를 Kubernetes API body로 변환"""
        body = {
            "apiVersion": "autoscaling.k8s.io/v1",
            "kind": "VerticalPodAutoscaler",
            "metadata": {
                "name": vpa.name,
                "namespace": vpa.namespace,
                "labels": vpa.labels,
                "annotations": vpa.annotations,
            },
            "spec": {
                "targetRef": {
                    "apiVersion": vpa.target_ref.api_version,
                    "kind": vpa.target_ref.kind,
                    "name": vpa.target_ref.name,
                },
                "updatePolicy": {
                    "updateMode": vpa.update_policy.update_mode
                }
            }
        }
        return body

    def _to_domain(self, raw_vpa: Dict[str, Any]) -> VerticalPodAutoscaler:
        """Kubernetes API 응답(dict)을 도메인 객체로 변환"""
        metadata = raw_vpa.get("metadata", {})
        spec = raw_vpa.get("spec", {})
        target_ref = spec.get("targetRef", {})
        update_policy = spec.get("updatePolicy", {})

        return VerticalPodAutoscaler(
            name=metadata.get("name"),
            namespace=metadata.get("namespace"),
            labels=metadata.get("labels", {}),
            annotations=metadata.get("annotations", {}),
            target_ref=VpaTargetRef(
                api_version=target_ref.get("apiVersion"),
                kind=target_ref.get("kind"),
                name=target_ref.get("name"),
            ),
            update_policy=VpaUpdatePolicy(
                update_mode=update_policy.get("updateMode", "Off")
            )
        )
