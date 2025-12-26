"""Pod 리소스 관리 클래스

주의: Pod는 직접 생성/삭제하지 않고, 조회/관찰만 수행합니다.
Pod 생성은 Deployment, StatefulSet 등의 컨트롤러를 통해 이루어집니다.
"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import V1Pod
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from core.logger import Logger, get_logger
from .exceptions import (
    PodReadException,
    PodListException,
)


class PodManager:
    """Pod 리소스를 조회/관찰하는 클래스
    
    주의: Pod는 직접 생성/삭제하지 않습니다.
    """

    def __init__(
        self,
        k8s_client: KubernetesClient,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def get_pod(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1Pod]:
        """Pod 비동기 조회

        Args:
            name: Pod 이름
            namespace: 네임스페이스

        Returns:
            V1Pod 객체 또는 None (존재하지 않으면)

        Raises:
            PodReadException: 조회 실패 시 (404 제외)
        """
        try:
            pod = await self.k8s_client.core_v1.read_namespaced_pod(
                name=name,
                namespace=namespace,
            )
            return pod

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"Pod 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise PodReadException(
                pod_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Pod 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise PodReadException(
                pod_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_pods(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1Pod]:
        """Pod 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1Pod 객체 리스트

        Raises:
            PodListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.core_v1.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.core_v1.list_pod_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.logger.error(
                f"Pod 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise PodListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Pod 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise PodListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """Pod 존재 여부 확인

        Args:
            name: Pod 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        pod = await self.get_pod(name, namespace)
        return pod is not None

    async def get_pod_status(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, any]]:
        """Pod 상태 조회

        Args:
            name: Pod 이름
            namespace: 네임스페이스

        Returns:
            Pod 상태 정보 딕셔너리 또는 None

        Raises:
            PodReadException: 조회 실패 시
        """
        pod = await self.get_pod(name, namespace)
        if not pod or not pod.status:
            return None

        status = pod.status
        return {
            "phase": status.phase,
            "pod_ip": status.pod_ip,
            "host_ip": status.host_ip,
            "start_time": status.start_time,
            "conditions": [
                {
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message,
                }
                for condition in (status.conditions or [])
            ],
            "container_statuses": [
                {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "image": cs.image,
                    "state": self._get_container_state(cs),
                }
                for cs in (status.container_statuses or [])
            ],
        }

    def _get_container_state(self, container_status) -> Dict[str, any]:
        """컨테이너 상태 추출

        Args:
            container_status: V1ContainerStatus 객체

        Returns:
            컨테이너 상태 딕셔너리
        """
        if not container_status.state:
            return {"state": "Unknown"}

        state = container_status.state
        if state.running:
            return {
                "state": "Running",
                "started_at": state.running.started_at,
            }
        elif state.waiting:
            return {
                "state": "Waiting",
                "reason": state.waiting.reason,
                "message": state.waiting.message,
            }
        elif state.terminated:
            return {
                "state": "Terminated",
                "exit_code": state.terminated.exit_code,
                "reason": state.terminated.reason,
                "message": state.terminated.message,
                "started_at": state.terminated.started_at,
                "finished_at": state.terminated.finished_at,
            }
        else:
            return {"state": "Unknown"}

    async def get_pod_logs(
        self,
        name: str,
        namespace: str,
        container: Optional[str] = None,
        tail_lines: Optional[int] = None,
        since_seconds: Optional[int] = None,
        timestamps: bool = False,
    ) -> Optional[str]:
        """Pod 로그 조회

        Args:
            name: Pod 이름
            namespace: 네임스페이스
            container: 컨테이너 이름 (None이면 첫 번째 컨테이너)
            tail_lines: 마지막 N줄만 조회
            since_seconds: 최근 N초 동안의 로그만 조회
            timestamps: 타임스탬프 포함 여부

        Returns:
            로그 문자열 또는 None

        Raises:
            PodReadException: 조회 실패 시
        """
        try:
            logs = await self.k8s_client.core_v1.read_namespaced_pod_log(
                name=name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
                since_seconds=since_seconds,
                timestamps=timestamps,
            )
            return logs

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"Pod 로그 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise PodReadException(
                pod_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Pod 로그 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise PodReadException(
                pod_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_pods_by_owner(
        self,
        owner_name: str,
        owner_kind: str,
        namespace: str,
    ) -> List[V1Pod]:
        """특정 소유자(Deployment, StatefulSet 등)의 Pod 목록 조회

        Args:
            owner_name: 소유자 이름
            owner_kind: 소유자 종류 (예: "Deployment", "StatefulSet")
            namespace: 네임스페이스

        Returns:
            V1Pod 객체 리스트

        Raises:
            PodListException: 목록 조회 실패 시
        """
        pods = await self.list_pods(namespace=namespace)
        
        # OwnerReferences로 필터링
        filtered_pods = []
        for pod in pods:
            if pod.metadata.owner_references:
                for owner_ref in pod.metadata.owner_references:
                    if (owner_ref.kind == owner_kind and 
                        owner_ref.name == owner_name):
                        filtered_pods.append(pod)
                        break
        
        return filtered_pods
