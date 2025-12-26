"""ServiceAccount 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1ServiceAccount,
    V1ObjectMeta,
    V1LocalObjectReference,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from core.logger import Logger, get_logger
from .exceptions import (
    ServiceAccountCreationException,
    ServiceAccountReadException,
    ServiceAccountUpdateException,
    ServiceAccountDeletionException,
    ServiceAccountListException,
)


class ServiceAccountManager:
    """ServiceAccount 리소스를 관리하는 클래스
    """

    def __init__(
        self,
        k8s_client: KubernetesClient,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_service_account(
        self,
        name: str,
        namespace: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        image_pull_secrets: Optional[List[str]] = None,
    ) -> V1ServiceAccount:
        """ServiceAccount 비동기 생성

        Args:
            name: ServiceAccount 이름
            namespace: 네임스페이스
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리
            image_pull_secrets: ImagePullSecret 이름 리스트

        Returns:
            생성되거나 기존에 존재하는 V1ServiceAccount 객체

        Raises:
            ServiceAccountCreationException: ServiceAccount 생성 실패 시
        """
        self.logger.info(
            f"ServiceAccount 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_service_account(name, namespace)
        if existing:
            self.logger.info(
                f"ServiceAccount 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # ImagePullSecret 객체 리스트 생성
        image_pull_secret_refs = None
        if image_pull_secrets:
            image_pull_secret_refs = [
                V1LocalObjectReference(name=secret_name)
                for secret_name in image_pull_secrets
            ]

        # ServiceAccount 객체 생성
        service_account = V1ServiceAccount(
            api_version="v1",
            kind="ServiceAccount",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {},
                annotations=annotations or {},
            ),
            image_pull_secrets=image_pull_secret_refs,
        )

        try:
            sa = await self.k8s_client.core_v1.create_namespaced_service_account(
                namespace=namespace,
                body=service_account,
            )
            self.logger.info(
                f"ServiceAccount 생성 완료: {name} (namespace: {namespace})"
            )
            return sa

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"ServiceAccount 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_service_account(name, namespace)
                if existing:
                    return existing

            self.logger.error(
                f"ServiceAccount 생성 실패: {name} - {e.reason}"
            )
            raise ServiceAccountCreationException(
                service_account_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"ServiceAccount 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceAccountCreationException(
                service_account_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_service_account(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1ServiceAccount]:
        """ServiceAccount 비동기 조회

        Args:
            name: ServiceAccount 이름
            namespace: 네임스페이스

        Returns:
            V1ServiceAccount 객체 또는 None (존재하지 않으면)

        Raises:
            ServiceAccountReadException: 조회 실패 시 (404 제외)
        """
        try:
            sa = await self.k8s_client.core_v1.read_namespaced_service_account(
                name=name,
                namespace=namespace,
            )
            return sa

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.error(
                f"ServiceAccount 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise ServiceAccountReadException(
                service_account_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                message=f"ServiceAccount 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceAccountReadException(
                service_account_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_service_account(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """ServiceAccount 비동기 삭제

        Args:
            name: ServiceAccount 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            ServiceAccountDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"ServiceAccount 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_service_account(name, namespace)
        if not existing:
            self.logger.warning(
                f"ServiceAccount가 존재하지 않음: {name} (namespace: {namespace})"
            )
            raise ServiceAccountDeletionException(
                service_account_name=name,
                namespace=namespace,
                reason="ServiceAccount does not exist",
            )

        try:
            await self.k8s_client.core_v1.delete_namespaced_service_account(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(
                f"ServiceAccount 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(
                    f"ServiceAccount 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.error(
                f"ServiceAccount 삭제 실패: {name} - {e.reason}"
            )
            raise ServiceAccountDeletionException(
                service_account_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"ServiceAccount 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceAccountDeletionException(
                service_account_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_service_accounts(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1ServiceAccount]:
        """ServiceAccount 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1ServiceAccount 객체 리스트

        Raises:
            ServiceAccountListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.core_v1.list_namespaced_service_account(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.core_v1.list_service_account_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.error(
                f"ServiceAccount 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise ServiceAccountListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"ServiceAccount 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise ServiceAccountListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """ServiceAccount 존재 여부 확인

        Args:
            name: ServiceAccount 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        sa = await self.get_service_account(name, namespace)
        return sa is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1ServiceAccount:
        """ServiceAccount 레이블 업데이트

        Args:
            name: ServiceAccount 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1ServiceAccount 객체

        Raises:
            ServiceAccountUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"ServiceAccount 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_service_account(name, namespace)
        if not existing:
            raise ServiceAccountUpdateException(
                service_account_name=name,
                namespace=namespace,
                reason="ServiceAccount does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            sa = await self.k8s_client.core_v1.patch_namespaced_service_account(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"ServiceAccount 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return sa

        except ApiException as e:
            self.logger.error(
                f"ServiceAccount 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise ServiceAccountUpdateException(
                service_account_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"ServiceAccount 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceAccountUpdateException(
                service_account_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_annotations(
        self,
        name: str,
        namespace: str,
        annotations: Dict[str, str],
        merge: bool = True,
    ) -> V1ServiceAccount:
        """ServiceAccount 어노테이션 업데이트

        Args:
            name: ServiceAccount 이름
            namespace: 네임스페이스
            annotations: 새로운 어노테이션 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1ServiceAccount 객체

        Raises:
            ServiceAccountUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"ServiceAccount 어노테이션 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_service_account(name, namespace)
        if not existing:
            raise ServiceAccountUpdateException(
                service_account_name=name,
                namespace=namespace,
                reason="ServiceAccount does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.annotations:
            new_annotations = {**existing.metadata.annotations, **annotations}
        else:
            new_annotations = annotations

        # Patch 요청
        body = {"metadata": {"annotations": new_annotations}}

        try:
            sa = await self.k8s_client.core_v1.patch_namespaced_service_account(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"ServiceAccount 어노테이션 업데이트 완료: {name} (namespace: {namespace})"
            )
            return sa

        except ApiException as e:
            self.logger.error(
                f"ServiceAccount 어노테이션 업데이트 실패: {name} - {e.reason}"
            )
            raise ServiceAccountUpdateException(
                service_account_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"ServiceAccount 어노테이션 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceAccountUpdateException(
                service_account_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def add_image_pull_secret(
        self,
        name: str,
        namespace: str,
        secret_name: str,
    ) -> V1ServiceAccount:
        """ServiceAccount에 ImagePullSecret 추가

        Args:
            name: ServiceAccount 이름
            namespace: 네임스페이스
            secret_name: 추가할 Secret 이름

        Returns:
            업데이트된 V1ServiceAccount 객체

        Raises:
            ServiceAccountUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"ServiceAccount에 ImagePullSecret 추가: {name} (secret: {secret_name})"
        )

        # 존재 여부 확인
        existing = await self.get_service_account(name, namespace)
        if not existing:
            raise ServiceAccountUpdateException(
                service_account_name=name,
                namespace=namespace,
                reason="ServiceAccount does not exist",
            )

        # 기존 ImagePullSecrets 가져오기
        image_pull_secrets = existing.image_pull_secrets or []

        # 이미 존재하는지 확인
        if any(secret.name == secret_name for secret in image_pull_secrets):
            self.logger.info(
                f"ImagePullSecret 이미 존재함: {secret_name}"
            )
            return existing

        # 새로운 Secret 추가
        image_pull_secrets.append(V1LocalObjectReference(name=secret_name))

        # Patch 요청
        body = {
            "imagePullSecrets": [
                {"name": secret.name} for secret in image_pull_secrets
            ]
        }

        try:
            sa = await self.k8s_client.core_v1.patch_namespaced_service_account(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"ImagePullSecret 추가 완료: {secret_name} → {name}"
            )
            return sa

        except ApiException as e:
            self.logger.error(
                f"ImagePullSecret 추가 실패: {name} - {e.reason}"
            )
            raise ServiceAccountUpdateException(
                service_account_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"ImagePullSecret 추가 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceAccountUpdateException(
                service_account_name=name,
                namespace=namespace,
                reason=str(e),
            )
