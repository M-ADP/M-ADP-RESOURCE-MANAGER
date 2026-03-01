from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class VpaTargetRef:
    """VPA가 타겟으로 하는 리소스 정보"""
    api_version: str
    kind: str
    name: str


@dataclass(frozen=True)
class VpaUpdatePolicy:
    """VPA의 업데이트 정책"""
    # "Off": VPA는 추천만 제공하고 파드를 변경하지 않음
    # "Initial": 파드 생성 시에만 리소스 요청을 할당
    # "Recreate": 파드를 재시작하여 리소스 요청을 업데이트
    # "Auto": 파드를 재시작할 수 있으면 재시작하여 리소스 요청을 업데이트
    update_mode: str = "Off"


@dataclass(frozen=True)
class VerticalPodAutoscaler:
    """VerticalPodAutoscaler (VPA) 도메인 객체"""
    name: str
    namespace: str
    target_ref: VpaTargetRef
    update_policy: VpaUpdatePolicy = field(default_factory=VpaUpdatePolicy)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def for_deployment(
        cls,
        name: str,
        namespace: str,
        deployment_name: str,
        update_mode: str = "Off",
    ) -> "VerticalPodAutoscaler":
        """특정 Deployment를 위한 VPA 객체를 생성합니다."""
        return cls(
            name=name,
            namespace=namespace,
            target_ref=VpaTargetRef(
                api_version="apps/v1",
                kind="Deployment",
                name=deployment_name,
            ),
            update_policy=VpaUpdatePolicy(update_mode=update_mode)
        )
