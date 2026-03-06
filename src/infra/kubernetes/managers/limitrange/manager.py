"""LimitRange 리소스 관리 클래스"""

from typing import Optional, List
from kubernetes_asyncio.client import (
    V1LimitRange,
    V1ObjectMeta,
    V1LimitRangeSpec,
    V1LimitRangeItem,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    LimitRangeCreationException,
    LimitRangeReadException,
    LimitRangeUpdateException,
    LimitRangeDeletionException,
    LimitRangeListException,
)


class LimitRangeManager:
    """LimitRange 리소스를 관리하는 클래스
    """

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_limitrange(
        self,
        name: str,
        namespace: str,
        limits: List[V1LimitRangeItem],
        labels: Optional[dict] = None,
        annotations: Optional[dict] = None,
    ) -> V1LimitRange:
        """LimitRange 비동기 생성

        Args:
            name: LimitRange 이름
            namespace: 네임스페이스
            limits: 리소스 제한 목록
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리

        Returns:
            생성되거나 기존에 존재하는 V1LimitRange 객체

        Raises:
            LimitRangeCreationException: LimitRange 생성 실패 시
        """
        self.logger.info(
            f"LimitRange 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_limitrange(name, namespace)
        if existing:
            self.logger.info(
                f"LimitRange 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # LimitRange 객체 생성
        limitrange = V1LimitRange(
            api_version="v1",
            kind="LimitRange",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {},
                annotations=annotations or {},
            ),
            spec=V1LimitRangeSpec(
                limits=limits,
            ),
        )

        try:
            lr = await self.k8s_client.core_v1.create_namespaced_limit_range(
                namespace=namespace,
                body=limitrange,
            )
            self.logger.info(
                f"LimitRange 생성 완료: {name} (namespace: {namespace})"
            )
            return lr

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"LimitRange 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_limitrange(name, namespace)
                if existing:
                    return existing

            self.logger.logger.error(
                f"LimitRange 생성 실패: {name} - {e.reason}"
            )
            raise LimitRangeCreationException(
                limitrange_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"LimitRange 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise LimitRangeCreationException(
                limitrange_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_limitrange(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1LimitRange]:
        """LimitRange 비동기 조회

        Args:
            name: LimitRange 이름
            namespace: 네임스페이스

        Returns:
            V1LimitRange 객체 또는 None (존재하지 않으면)

        Raises:
            LimitRangeReadException: 조회 실패 시 (404 제외)
        """
        try:
            lr = await self.k8s_client.core_v1.read_namespaced_limit_range(
                name=name,
                namespace=namespace,
            )
            return lr

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"LimitRange 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise LimitRangeReadException(
                limitrange_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"LimitRange 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise LimitRangeReadException(
                limitrange_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_limitrange(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """LimitRange 비동기 삭제

        Args:
            name: LimitRange 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            LimitRangeDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"LimitRange 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_limitrange(name, namespace)
        if not existing:
            self.logger.warning(
                f"LimitRange가 존재하지 않음: {name} (namespace: {namespace})"
            )
            raise LimitRangeDeletionException(
                limitrange_name=name,
                namespace=namespace,
                reason="LimitRange does not exist",
            )

        try:
            await self.k8s_client.core_v1.delete_namespaced_limit_range(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(
                f"LimitRange 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(
                    f"LimitRange 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.logger.error(
                f"LimitRange 삭제 실패: {name} - {e.reason}"
            )
            raise LimitRangeDeletionException(
                limitrange_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"LimitRange 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise LimitRangeDeletionException(
                limitrange_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_limitranges(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1LimitRange]:
        """LimitRange 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app_deployment=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1LimitRange 객체 리스트

        Raises:
            LimitRangeListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.core_v1.list_namespaced_limit_range(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.core_v1.list_limit_range_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.logger.error(
                f"LimitRange 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise LimitRangeListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"LimitRange 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise LimitRangeListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """LimitRange 존재 여부 확인

        Args:
            name: LimitRange 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        lr = await self.get_limitrange(name, namespace)
        return lr is not None

    async def update_limits(
        self,
        name: str,
        namespace: str,
        limits: List[V1LimitRangeItem],
    ) -> V1LimitRange:
        """LimitRange 제한 사항 업데이트

        Args:
            name: LimitRange 이름
            namespace: 네임스페이스
            limits: 새로운 리소스 제한 목록

        Returns:
            업데이트된 V1LimitRange 객체

        Raises:
            LimitRangeUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"LimitRange 제한 사항 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_limitrange(name, namespace)
        if not existing:
            raise LimitRangeUpdateException(
                limitrange_name=name,
                namespace=namespace,
                reason="LimitRange does not exist",
            )

        # Patch 요청
        body = {"spec": {"limits": [limit.to_dict() for limit in limits]}}

        try:
            lr = await self.k8s_client.core_v1.patch_namespaced_limit_range(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"LimitRange 제한 사항 업데이트 완료: {name} (namespace: {namespace})"
            )
            return lr

        except ApiException as e:
            self.logger.logger.error(
                f"LimitRange 제한 사항 업데이트 실패: {name} - {e.reason}"
            )
            raise LimitRangeUpdateException(
                limitrange_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"LimitRange 제한 사항 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise LimitRangeUpdateException(
                limitrange_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: dict,
        merge: bool = True,
    ) -> V1LimitRange:
        """LimitRange 레이블 업데이트

        Args:
            name: LimitRange 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1LimitRange 객체

        Raises:
            LimitRangeUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"LimitRange 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_limitrange(name, namespace)
        if not existing:
            raise LimitRangeUpdateException(
                limitrange_name=name,
                namespace=namespace,
                reason="LimitRange does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            lr = await self.k8s_client.core_v1.patch_namespaced_limit_range(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"LimitRange 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return lr

        except ApiException as e:
            self.logger.logger.error(
                f"LimitRange 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise LimitRangeUpdateException(
                limitrange_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"LimitRange 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise LimitRangeUpdateException(
                limitrange_name=name,
                namespace=namespace,
                reason=str(e),
            )
