"""ResourceQuota 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1ResourceQuota,
    V1ObjectMeta,
    V1ResourceQuotaSpec,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    ResourceQuotaCreationException,
    ResourceQuotaReadException,
    ResourceQuotaUpdateException,
    ResourceQuotaDeletionException,
    ResourceQuotaListException,
)


class ResourceQuotaManager:
    """ResourceQuota 리소스를 관리하는 클래스

    ResourceQuota는 네임스페이스별 리소스 사용량을 제한하는 Kubernetes 리소스입니다.
    CPU, 메모리, 파드 수, 서비스 수 등 다양한 리소스 제한을 설정할 수 있습니다.
    """

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_resource_quota(
        self,
        name: str,
        namespace: str,
        hard_limits: Dict[str, str],
        scope_selector: Optional[Dict] = None,
        scopes: Optional[List[str]] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> V1ResourceQuota:
        """ResourceQuota 비동기 생성

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스
            hard_limits: 리소스 제한 딕셔너리 (예: {"cpu": "10", "memory": "20Gi", "pods": "50"})
            scope_selector: 스코프 셀렉터 (선택적)
            scopes: 스코프 목록 (선택적)
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리

        Returns:
            생성되거나 기존에 존재하는 V1ResourceQuota 객체

        Raises:
            ResourceQuotaCreationException: ResourceQuota 생성 실패 시
        """
        self.logger.info(
            f"ResourceQuota 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_resource_quota(name, namespace)
        if existing:
            self.logger.info(
                f"ResourceQuota 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # ResourceQuota 객체 생성
        spec = V1ResourceQuotaSpec(
            hard=hard_limits,
            scope_selector=scope_selector,
            scopes=scopes,
        )

        resource_quota = V1ResourceQuota(
            api_version="v1",
            kind="ResourceQuota",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {},
                annotations=annotations or {},
            ),
            spec=spec,
        )

        try:
            rq = await self.k8s_client.core_v1.create_namespaced_resource_quota(
                namespace=namespace,
                body=resource_quota,
            )
            self.logger.info(
                f"ResourceQuota 생성 완료: {name} (namespace: {namespace})"
            )
            return rq

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"ResourceQuota 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_resource_quota(name, namespace)
                if existing:
                    return existing

            self.logger.logger.error(
                f"ResourceQuota 생성 실패: {name} - {e.reason}"
            )
            raise ResourceQuotaCreationException(
                resourcequota_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ResourceQuota 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise ResourceQuotaCreationException(
                resourcequota_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_resource_quota(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1ResourceQuota]:
        """ResourceQuota 비동기 조회

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스

        Returns:
            V1ResourceQuota 객체 또는 None (존재하지 않으면)

        Raises:
            ResourceQuotaReadException: 조회 실패 시 (404 제외)
        """
        try:
            rq = await self.k8s_client.core_v1.read_namespaced_resource_quota(
                name=name,
                namespace=namespace,
            )
            return rq

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"ResourceQuota 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise ResourceQuotaReadException(
                resourcequota_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ResourceQuota 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise ResourceQuotaReadException(
                resourcequota_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_resource_quota(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """ResourceQuota 비동기 삭제

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            ResourceQuotaDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"ResourceQuota 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_resource_quota(name, namespace)
        if not existing:
            self.logger.warning(
                f"ResourceQuota가 존재하지 않음: {name} (namespace: {namespace})"
            )
            raise ResourceQuotaDeletionException(
                resourcequota_name=name,
                namespace=namespace,
                reason="ResourceQuota does not exist",
            )

        try:
            await self.k8s_client.core_v1.delete_namespaced_resource_quota(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(
                f"ResourceQuota 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(
                    f"ResourceQuota 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.logger.error(
                f"ResourceQuota 삭제 실패: {name} - {e.reason}"
            )
            raise ResourceQuotaDeletionException(
                resourcequota_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ResourceQuota 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise ResourceQuotaDeletionException(
                resourcequota_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_resource_quotas(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1ResourceQuota]:
        """ResourceQuota 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1ResourceQuota 객체 리스트

        Raises:
            ResourceQuotaListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.core_v1.list_namespaced_resource_quota(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.core_v1.list_resource_quota_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.logger.error(
                f"ResourceQuota 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise ResourceQuotaListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ResourceQuota 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise ResourceQuotaListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """ResourceQuota 존재 여부 확인

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        rq = await self.get_resource_quota(name, namespace)
        return rq is not None

    async def update_resource_quota(
        self,
        name: str,
        namespace: str,
        hard_limits: Dict[str, str],
        scope_selector: Optional[Dict] = None,
        scopes: Optional[List[str]] = None,
    ) -> V1ResourceQuota:
        """ResourceQuota 리소스 제한 업데이트

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스
            hard_limits: 새로운 리소스 제한 딕셔너리
            scope_selector: 스코프 셀렉터 (선택적)
            scopes: 스코프 목록 (선택적)

        Returns:
            업데이트된 V1ResourceQuota 객체

        Raises:
            ResourceQuotaUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"ResourceQuota 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_resource_quota(name, namespace)
        if not existing:
            raise ResourceQuotaUpdateException(
                resourcequota_name=name,
                namespace=namespace,
                reason="ResourceQuota does not exist",
            )

        # Spec 업데이트
        spec_update = {"hard": hard_limits}
        if scope_selector is not None:
            spec_update["scopeSelector"] = scope_selector
        if scopes is not None:
            spec_update["scopes"] = scopes

        body = {"spec": spec_update}

        try:
            rq = await self.k8s_client.core_v1.patch_namespaced_resource_quota(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"ResourceQuota 업데이트 완료: {name} (namespace: {namespace})"
            )
            return rq

        except ApiException as e:
            self.logger.logger.error(
                f"ResourceQuota 업데이트 실패: {name} - {e.reason}"
            )
            raise ResourceQuotaUpdateException(
                resourcequota_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ResourceQuota 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ResourceQuotaUpdateException(
                resourcequota_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_quota_status(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, Dict[str, str]]]:
        """ResourceQuota 사용량 vs 제한 조회

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스

        Returns:
            {
                "hard": {"cpu": "10", "memory": "20Gi", ...},
                "used": {"cpu": "5", "memory": "10Gi", ...}
            }
            또는 None (존재하지 않으면)

        Raises:
            ResourceQuotaReadException: 조회 실패 시
        """
        rq = await self.get_resource_quota(name, namespace)
        if not rq:
            return None

        status = {
            "hard": rq.spec.hard if rq.spec and rq.spec.hard else {},
            "used": rq.status.used if rq.status and rq.status.used else {},
        }

        return status

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1ResourceQuota:
        """ResourceQuota 레이블 업데이트

        Args:
            name: ResourceQuota 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1ResourceQuota 객체

        Raises:
            ResourceQuotaUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"ResourceQuota 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_resource_quota(name, namespace)
        if not existing:
            raise ResourceQuotaUpdateException(
                resourcequota_name=name,
                namespace=namespace,
                reason="ResourceQuota does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            rq = await self.k8s_client.core_v1.patch_namespaced_resource_quota(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"ResourceQuota 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return rq

        except ApiException as e:
            self.logger.logger.error(
                f"ResourceQuota 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise ResourceQuotaUpdateException(
                resourcequota_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ResourceQuota 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ResourceQuotaUpdateException(
                resourcequota_name=name,
                namespace=namespace,
                reason=str(e),
            )
