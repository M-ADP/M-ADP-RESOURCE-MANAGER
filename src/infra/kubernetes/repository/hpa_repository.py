"""HPA Repository 구현체"""

from typing import List, Optional

from kubernetes_asyncio.client import V2HorizontalPodAutoscaler

from src.core.kubernetes.hpa import (
    HorizontalPodAutoscaler,
    HpaRepository,
    HpaScaleTargetRef,
    HpaMetricSpec,
    HpaStatus,
)
from src.infra.kubernetes.managers.hpa import HpaManager


class K8sHpaRepository(HpaRepository):
    """Kubernetes HPA Repository 구현체"""

    def __init__(self, manager: HpaManager):
        self._manager = manager

    async def save(self, hpa: HorizontalPodAutoscaler) -> HorizontalPodAutoscaler:
        """HPA 저장 (생성 또는 업데이트)"""
        metrics = [
            {
                "type": m.type,
                "resource_name": m.resource_name,
                "target_type": m.target_type,
                "target_value": m.target_value,
            }
            for m in hpa.metrics
        ]

        raw_hpa = await self._manager.create_hpa(
            name=hpa.name,
            namespace=hpa.namespace,
            target_ref_name=hpa.scale_target_ref.name,
            target_ref_kind=hpa.scale_target_ref.kind,
            target_ref_api_version=hpa.scale_target_ref.api_version,
            min_replicas=hpa.min_replicas,
            max_replicas=hpa.max_replicas,
            metrics=metrics,
            labels=hpa.labels,
            annotations=hpa.annotations,
        )
        return self._to_domain(raw_hpa)

    async def find_by_name(self, name: str, namespace: str) -> Optional[HorizontalPodAutoscaler]:
        """이름으로 HPA 조회"""
        raw_hpa = await self._manager.get_hpa(name, namespace)
        return self._to_domain(raw_hpa) if raw_hpa else None

    async def find_all(self, namespace: str) -> List[HorizontalPodAutoscaler]:
        """네임스페이스 내의 모든 HPA 조회"""
        raw_hpas = await self._manager.list_hpas(namespace)
        return [self._to_domain(h) for h in raw_hpas]

    async def delete(self, name: str, namespace: str) -> bool:
        """HPA 삭제"""
        return await self._manager.delete_hpa(name, namespace)

    def _to_domain(self, raw_hpa: V2HorizontalPodAutoscaler) -> HorizontalPodAutoscaler:
        """Kubernetes API 응답을 도메인 객체로 변환"""
        metadata = raw_hpa.metadata
        spec = raw_hpa.spec
        status = raw_hpa.status

        # Scale Target Ref 변환
        scale_target_ref = HpaScaleTargetRef(
            api_version=spec.scale_target_ref.api_version,
            kind=spec.scale_target_ref.kind,
            name=spec.scale_target_ref.name,
        )

        # Metrics 변환
        metrics = []
        if spec.metrics:
            for m in spec.metrics:
                if m.type == "Resource" and m.resource:
                    target_type = m.resource.target.type if m.resource.target else "Utilization"
                    target_value = (
                        m.resource.target.average_utilization
                        if target_type == "Utilization"
                        else m.resource.target.average_value
                    )
                    metrics.append(
                        HpaMetricSpec(
                            type="Resource",
                            resource_name=m.resource.name,
                            target_type=target_type,
                            target_value=int(target_value) if target_value else 0,
                        )
                    )

        # Status 변환
        hpa_status = None
        if status:
            current_cpu = None
            current_memory = None
            if status.current_metrics:
                for cm in status.current_metrics:
                    if cm.type == "Resource" and cm.resource:
                        if cm.resource.name == "cpu" and cm.resource.current:
                            current_cpu = cm.resource.current.average_utilization
                        elif cm.resource.name == "memory" and cm.resource.current:
                            current_memory = cm.resource.current.average_utilization

            hpa_status = HpaStatus(
                current_replicas=status.current_replicas,
                desired_replicas=status.desired_replicas,
                current_cpu_utilization=current_cpu,
                current_memory_utilization=current_memory,
            )

        return HorizontalPodAutoscaler(
            name=metadata.name,
            namespace=metadata.namespace,
            scale_target_ref=scale_target_ref,
            min_replicas=spec.min_replicas or 1,
            max_replicas=spec.max_replicas,
            metrics=metrics,
            labels=metadata.labels or {},
            annotations=metadata.annotations or {},
            status=hpa_status,
        )
