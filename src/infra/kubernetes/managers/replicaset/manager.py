"""ReplicaSet 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1ReplicaSet,
    V1ObjectMeta,
    V1ReplicaSetSpec,
    V1LabelSelector,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    ReplicaSetCreationException,
    ReplicaSetReadException,
    ReplicaSetUpdateException,
    ReplicaSetDeletionException,
    ReplicaSetListException,
)


class ReplicaSetManager:
    """ReplicaSet 리소스를 관리하는 클래스
    """

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_replicaset(
        self,
        name: str,
        namespace: str,
        containers: List[V1Container],
        replicas: int = 1,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        selector_labels: Optional[Dict[str, str]] = None,
        pod_labels: Optional[Dict[str, str]] = None,
        pod_annotations: Optional[Dict[str, str]] = None,
    ) -> V1ReplicaSet:
        """ReplicaSet 비동기 생성

        Args:
            name: ReplicaSet 이름
            namespace: 네임스페이스
            containers: 컨테이너 리스트
            replicas: 레플리카 수
            labels: ReplicaSet 레이블
            annotations: ReplicaSet 어노테이션
            selector_labels: Pod 셀렉터 레이블 (None이면 labels 사용)
            pod_labels: Pod 레이블 (None이면 labels 사용)
            pod_annotations: Pod 어노테이션

        Returns:
            생성되거나 기존에 존재하는 V1ReplicaSet 객체

        Raises:
            ReplicaSetCreationException: ReplicaSet 생성 실패 시
        """
        self.logger.info(
            f"ReplicaSet 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_replicaset(name, namespace)
        if existing:
            self.logger.info(
                f"ReplicaSet 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # 기본 레이블 설정
        replicaset_labels = labels or {"app": name}
        selector_match_labels = selector_labels or replicaset_labels
        pod_template_labels = pod_labels or replicaset_labels

        # ReplicaSet 객체 생성
        replicaset = V1ReplicaSet(
            api_version="apps/v1",
            kind="ReplicaSet",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=replicaset_labels,
                annotations=annotations or {},
            ),
            spec=V1ReplicaSetSpec(
                replicas=replicas,
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
            rs = await self.k8s_client.apps_v1.create_namespaced_replica_set(
                namespace=namespace,
                body=replicaset,
            )
            self.logger.info(
                f"ReplicaSet 생성 완료: {name} (namespace: {namespace})"
            )
            return rs

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"ReplicaSet 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_replicaset(name, namespace)
                if existing:
                    return existing

            self.logger.logger.error(
                f"ReplicaSet 생성 실패: {name} - {e.reason}"
            )
            raise ReplicaSetCreationException(
                replicaset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ReplicaSet 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise ReplicaSetCreationException(
                replicaset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_replicaset(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1ReplicaSet]:
        """ReplicaSet 비동기 조회

        Args:
            name: ReplicaSet 이름
            namespace: 네임스페이스

        Returns:
            V1ReplicaSet 객체 또는 None (존재하지 않으면)

        Raises:
            ReplicaSetReadException: 조회 실패 시 (404 제외)
        """
        try:
            rs = await self.k8s_client.apps_v1.read_namespaced_replica_set(
                name=name,
                namespace=namespace,
            )
            return rs

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"ReplicaSet 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise ReplicaSetReadException(
                replicaset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ReplicaSet 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise ReplicaSetReadException(
                replicaset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_replicaset(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """ReplicaSet 비동기 삭제

        Args:
            name: ReplicaSet 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            ReplicaSetDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"ReplicaSet 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_replicaset(name, namespace)
        if not existing:
            self.logger.warning(
                f"ReplicaSet가 존재하지 않음: {name} (namespace: {namespace})"
            )
            raise ReplicaSetDeletionException(
                replicaset_name=name,
                namespace=namespace,
                reason="ReplicaSet does not exist",
            )

        try:
            await self.k8s_client.apps_v1.delete_namespaced_replica_set(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(
                f"ReplicaSet 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(
                    f"ReplicaSet 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.logger.error(
                f"ReplicaSet 삭제 실패: {name} - {e.reason}"
            )
            raise ReplicaSetDeletionException(
                replicaset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ReplicaSet 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise ReplicaSetDeletionException(
                replicaset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_replicasets(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1ReplicaSet]:
        """ReplicaSet 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1ReplicaSet 객체 리스트

        Raises:
            ReplicaSetListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.apps_v1.list_namespaced_replica_set(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.apps_v1.list_replica_set_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.logger.error(
                f"ReplicaSet 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise ReplicaSetListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ReplicaSet 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise ReplicaSetListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """ReplicaSet 존재 여부 확인

        Args:
            name: ReplicaSet 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        rs = await self.get_replicaset(name, namespace)
        return rs is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1ReplicaSet:
        """ReplicaSet 레이블 업데이트

        Args:
            name: ReplicaSet 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1ReplicaSet 객체

        Raises:
            ReplicaSetUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"ReplicaSet 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_replicaset(name, namespace)
        if not existing:
            raise ReplicaSetUpdateException(
                replicaset_name=name,
                namespace=namespace,
                reason="ReplicaSet does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            rs = await self.k8s_client.apps_v1.patch_namespaced_replica_set(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"ReplicaSet 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return rs

        except ApiException as e:
            self.logger.logger.error(
                f"ReplicaSet 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise ReplicaSetUpdateException(
                replicaset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ReplicaSet 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ReplicaSetUpdateException(
                replicaset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_replicas(
        self,
        name: str,
        namespace: str,
        replicas: int,
    ) -> V1ReplicaSet:
        """ReplicaSet 레플리카 수 업데이트

        Args:
            name: ReplicaSet 이름
            namespace: 네임스페이스
            replicas: 새로운 레플리카 수

        Returns:
            업데이트된 V1ReplicaSet 객체

        Raises:
            ReplicaSetUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"ReplicaSet 레플리카 수 업데이트: {name} (namespace: {namespace}, replicas: {replicas})"
        )

        # 존재 여부 확인
        existing = await self.get_replicaset(name, namespace)
        if not existing:
            raise ReplicaSetUpdateException(
                replicaset_name=name,
                namespace=namespace,
                reason="ReplicaSet does not exist",
            )

        # Patch 요청
        body = {"spec": {"replicas": replicas}}

        try:
            rs = await self.k8s_client.apps_v1.patch_namespaced_replica_set(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"ReplicaSet 레플리카 수 업데이트 완료: {name} (namespace: {namespace})"
            )
            return rs

        except ApiException as e:
            self.logger.logger.error(
                f"ReplicaSet 레플리카 수 업데이트 실패: {name} - {e.reason}"
            )
            raise ReplicaSetUpdateException(
                replicaset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ReplicaSet 레플리카 수 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ReplicaSetUpdateException(
                replicaset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_replicaset_status(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, any]]:
        """ReplicaSet 상태 조회

        Args:
            name: ReplicaSet 이름
            namespace: 네임스페이스

        Returns:
            ReplicaSet 상태 정보 딕셔너리 또는 None

        Raises:
            ReplicaSetReadException: 조회 실패 시
        """
        replicaset = await self.get_replicaset(name, namespace)
        if not replicaset or not replicaset.status:
            return None

        status = replicaset.status
        return {
            "replicas": status.replicas,
            "ready_replicas": status.ready_replicas,
            "available_replicas": status.available_replicas,
            "fully_labeled_replicas": status.fully_labeled_replicas,
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
