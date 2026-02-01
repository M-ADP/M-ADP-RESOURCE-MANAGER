from typing import List, Optional

from kubernetes_asyncio.client import V1Pod, V1Event

from src.core.kubernetes.pod import Pod, PodLogs, Event, PodRepository
from src.infra.kubernetes.managers.pod import PodManager


class K8sPodRepository(PodRepository):
    """Kubernetes Pod Repository 구현체"""

    def __init__(self, manager: PodManager):
        self._manager = manager

    async def find_by_deployment(
        self,
        deployment_name: str,
        namespace: str,
    ) -> List[Pod]:
        """Deployment 소속 Pod 목록 조회

        Deployment -> ReplicaSet -> Pod 관계를 통해 조회합니다.
        label selector를 사용하여 해당 Deployment의 Pod를 찾습니다.
        """
        v1_pods = await self._manager.list_pods(
            namespace=namespace,
            label_selector=f"app={deployment_name}",
        )
        return [self._to_domain(p) for p in v1_pods]

    async def get_logs(
        self,
        pod_name: str,
        namespace: str,
        tail_lines: Optional[int] = None,
        since_seconds: Optional[int] = None,
        timestamps: bool = False,
    ) -> Optional[PodLogs]:
        """Pod 로그 조회"""
        logs = await self._manager.get_pod_logs(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
            since_seconds=since_seconds,
            timestamps=timestamps,
        )
        if logs is None:
            return None
        return PodLogs(
            pod_name=pod_name,
            namespace=namespace,
            logs=logs,
        )

    async def get_events_by_deployment(
        self,
        deployment_name: str,
        namespace: str,
    ) -> List[Event]:
        """Deployment 관련 이벤트 조회

        Deployment, ReplicaSet, Pod 관련 이벤트를 모두 조회합니다.
        """
        result = await self._manager.k8s_client.core_v1.list_namespaced_event(
            namespace=namespace,
        )

        events = []
        for event in result.items:
            obj = event.involved_object
            # Deployment 자체 이벤트
            if obj.kind == "Deployment" and obj.name == deployment_name:
                events.append(self._event_to_domain(event))
            # ReplicaSet 이벤트 (deployment_name으로 시작)
            elif obj.kind == "ReplicaSet" and obj.name.startswith(f"{deployment_name}-"):
                events.append(self._event_to_domain(event))
            # Pod 이벤트 (deployment_name으로 시작)
            elif obj.kind == "Pod" and obj.name.startswith(f"{deployment_name}-"):
                events.append(self._event_to_domain(event))

        # 최신 이벤트가 먼저 오도록 정렬
        events.sort(
            key=lambda e: e.last_timestamp or e.first_timestamp or "",
            reverse=True,
        )
        return events

    def _to_domain(self, v1_pod: V1Pod) -> Pod:
        """V1Pod -> Pod 도메인 변환"""
        return Pod(
            name=v1_pod.metadata.name,
            namespace=v1_pod.metadata.namespace,
            phase=v1_pod.status.phase if v1_pod.status else None,
        )

    def _event_to_domain(self, v1_event: V1Event) -> Event:
        """V1Event -> Event 도메인 변환"""
        return Event(
            type=v1_event.type or "Normal",
            reason=v1_event.reason or "",
            message=v1_event.message or "",
            involved_object_kind=v1_event.involved_object.kind,
            involved_object_name=v1_event.involved_object.name,
            first_timestamp=v1_event.first_timestamp,
            last_timestamp=v1_event.last_timestamp,
            count=v1_event.count,
        )
