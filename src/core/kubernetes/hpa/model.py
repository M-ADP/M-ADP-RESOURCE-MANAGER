"""HPA 도메인 모델"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class HpaMetricSpec:
    """HPA 메트릭 스펙"""
    type: str  # "Resource"
    resource_name: str  # "cpu" | "memory"
    target_type: str  # "Utilization" | "AverageValue"
    target_value: int  # 사용률(%) 또는 평균값


@dataclass(frozen=True)
class HpaScaleTargetRef:
    """HPA가 타겟으로 하는 리소스 정보"""
    api_version: str
    kind: str
    name: str


@dataclass(frozen=True)
class HpaStatus:
    """HPA 상태 정보"""
    current_replicas: Optional[int] = None
    desired_replicas: Optional[int] = None
    current_cpu_utilization: Optional[int] = None
    current_memory_utilization: Optional[int] = None


@dataclass(frozen=True)
class HorizontalPodAutoscaler:
    """HorizontalPodAutoscaler (HPA) 도메인 객체"""
    name: str
    namespace: str
    scale_target_ref: HpaScaleTargetRef
    min_replicas: int = 1
    max_replicas: int = 10
    metrics: List[HpaMetricSpec] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    status: Optional[HpaStatus] = None

    @classmethod
    def for_deployment(
        cls,
        name: str,
        namespace: str,
        deployment_name: str,
        min_replicas: int = 1,
        max_replicas: int = 10,
        target_cpu_utilization: int = 80,
        target_memory_utilization: Optional[int] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> "HorizontalPodAutoscaler":
        """특정 Deployment를 위한 HPA 객체를 생성합니다."""
        metrics = [
            HpaMetricSpec(
                type="Resource",
                resource_name="cpu",
                target_type="Utilization",
                target_value=target_cpu_utilization,
            )
        ]

        if target_memory_utilization is not None:
            metrics.append(
                HpaMetricSpec(
                    type="Resource",
                    resource_name="memory",
                    target_type="Utilization",
                    target_value=target_memory_utilization,
                )
            )

        return cls(
            name=name,
            namespace=namespace,
            scale_target_ref=HpaScaleTargetRef(
                api_version="apps/v1",
                kind="Deployment",
                name=deployment_name,
            ),
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            metrics=metrics,
            labels=labels or {},
        )
