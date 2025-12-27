"""DaemonSet 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1DaemonSet,
    V1ObjectMeta,
    V1DaemonSetSpec,
    V1LabelSelector,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from core.logger import Logger, get_logger
from .exceptions import (
    DaemonSetCreationException,
    DaemonSetReadException,
    DaemonSetUpdateException,
    DaemonSetDeletionException,
    DaemonSetListException,
)


class DaemonSetManager:
    """DaemonSet 리소스를 관리하는 클래스
    """

    def __init__(
        self,
        k8s_client: KubernetesClient,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_daemonset(
        self,
        name: str,
        namespace: str,
        containers: List[V1Container],
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        selector_labels: Optional[Dict[str, str]] = None,
        pod_labels: Optional[Dict[str, str]] = None,
        pod_annotations: Optional[Dict[str, str]] = None,
    ) -> V1DaemonSet:
        """DaemonSet 비동기 생성

        Args:
            name: DaemonSet 이름
            namespace: 네임스페이스
            containers: 컨테이너 리스트
            labels: DaemonSet 레이블
            annotations: DaemonSet 어노테이션
            selector_labels: Pod 셀렉터 레이블 (None이면 labels 사용)
            pod_labels: Pod 레이블 (None이면 labels 사용)
            pod_annotations: Pod 어노테이션

        Returns:
            생성되거나 기존에 존재하는 V1DaemonSet 객체

        Raises:
            DaemonSetCreationException: DaemonSet 생성 실패 시
        """
        self.logger.info(
            f"DaemonSet 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_daemonset(name, namespace)
        if existing:
            self.logger.info(
                f"DaemonSet 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # 기본 레이블 설정
        daemonset_labels = labels or {"app": name}
        selector_match_labels = selector_labels or daemonset_labels
        pod_template_labels = pod_labels or daemonset_labels

        # DaemonSet 객체 생성
        daemonset = V1DaemonSet(
            api_version="apps/v1",
            kind="DaemonSet",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=daemonset_labels,
                annotations=annotations or {},
            ),
            spec=V1DaemonSetSpec(
                selector=V1LabelSelector(
                    match_labels=selector_match_labels,
                ),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(
                        labels=pod_template_labels,
                        annotations=pod_annotations or {},
                    ),
                    spec=V1PodSpec(
                        containers=containers,
                    ),
                ),
            ),
        )

        try:
            ds = await self.k8s_client.apps_v1.create_namespaced_daemon_set(
                namespace=namespace,
                body=daemonset,
            )
            self.logger.info(
                f"DaemonSet 생성 완료: {name} (namespace: {namespace})"
            )
            return ds

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"DaemonSet 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_daemonset(name, namespace)
                if existing:
                    return existing

            self.logger.logger.error(
                f"DaemonSet 생성 실패: {name} - {e.reason}"
            )
            raise DaemonSetCreationException(
                daemonset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"DaemonSet 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise DaemonSetCreationException(
                daemonset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_daemonset(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1DaemonSet]:
        """DaemonSet 비동기 조회

        Args:
            name: DaemonSet 이름
            namespace: 네임스페이스

        Returns:
            V1DaemonSet 객체 또는 None (존재하지 않으면)

        Raises:
            DaemonSetReadException: 조회 실패 시 (404 제외)
        """
        try:
            ds = await self.k8s_client.apps_v1.read_namespaced_daemon_set(
                name=name,
                namespace=namespace,
            )
            return ds

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"DaemonSet 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise DaemonSetReadException(
                daemonset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"DaemonSet 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise DaemonSetReadException(
                daemonset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_daemonset(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """DaemonSet 비동기 삭제

        Args:
            name: DaemonSet 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            DaemonSetDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"DaemonSet 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_daemonset(name, namespace)
        if not existing:
            self.logger.warning(
                f"DaemonSet가 존재하지 않음: {name} (namespace: {namespace})"
            )
            raise DaemonSetDeletionException(
                daemonset_name=name,
                namespace=namespace,
                reason="DaemonSet does not exist",
            )

        try:
            await self.k8s_client.apps_v1.delete_namespaced_daemon_set(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(
                f"DaemonSet 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(
                    f"DaemonSet 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.logger.error(
                f"DaemonSet 삭제 실패: {name} - {e.reason}"
            )
            raise DaemonSetDeletionException(
                daemonset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"DaemonSet 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise DaemonSetDeletionException(
                daemonset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_daemonsets(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1DaemonSet]:
        """DaemonSet 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1DaemonSet 객체 리스트

        Raises:
            DaemonSetListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.apps_v1.list_namespaced_daemon_set(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.apps_v1.list_daemon_set_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.logger.error(
                f"DaemonSet 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise DaemonSetListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"DaemonSet 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise DaemonSetListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """DaemonSet 존재 여부 확인

        Args:
            name: DaemonSet 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        ds = await self.get_daemonset(name, namespace)
        return ds is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1DaemonSet:
        """DaemonSet 레이블 업데이트

        Args:
            name: DaemonSet 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1DaemonSet 객체

        Raises:
            DaemonSetUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"DaemonSet 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_daemonset(name, namespace)
        if not existing:
            raise DaemonSetUpdateException(
                daemonset_name=name,
                namespace=namespace,
                reason="DaemonSet does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            ds = await self.k8s_client.apps_v1.patch_namespaced_daemon_set(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"DaemonSet 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return ds

        except ApiException as e:
            self.logger.logger.error(
                f"DaemonSet 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise DaemonSetUpdateException(
                daemonset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"DaemonSet 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise DaemonSetUpdateException(
                daemonset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_daemonset_status(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, any]]:
        """DaemonSet 상태 조회

        Args:
            name: DaemonSet 이름
            namespace: 네임스페이스

        Returns:
            DaemonSet 상태 정보 딕셔너리 또는 None

        Raises:
            DaemonSetReadException: 조회 실패 시
        """
        daemonset = await self.get_daemonset(name, namespace)
        if not daemonset or not daemonset.status:
            return None

        status = daemonset.status
        return {
            "current_number_scheduled": status.current_number_scheduled,
            "desired_number_scheduled": status.desired_number_scheduled,
            "number_available": status.number_available,
            "number_misscheduled": status.number_misscheduled,
            "number_ready": status.number_ready,
            "number_unavailable": status.number_unavailable,
            "updated_number_scheduled": status.updated_number_scheduled,
            "conditions": [
                {
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message,
                }
                for condition in (status.conditions or [])
            ],
        }
