"""Role 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1Role,
    V1ObjectMeta,
    V1PolicyRule,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    RoleCreationException,
    RoleReadException,
    RoleUpdateException,
    RoleDeletionException,
    RoleListException,
)


class RoleManager:
    """Role 리소스를 관리하는 클래스

    Args:
        k8s_client: KubernetesClientImpl 인스턴스
        logger: Logger 인스턴스 (선택적)
    """

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_role(
        self,
        name: str,
        namespace: str,
        rules: List[Dict[str, List[str]]],
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> V1Role:
        """Role 비동기 생성 (멱등성 보장)

        Args:
            name: Role 이름
            namespace: 네임스페이스
            rules: Policy rule 리스트 (예: [{"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list"]}])
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리

        Returns:
            생성되거나 기존에 존재하는 V1Role 객체

        Raises:
            RoleCreationException: Role 생성 실패 시
        """
        self.logger.info(f"Role 생성 시도: {name} (namespace: {namespace})")

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_role(name, namespace)
        if existing:
            self.logger.info(f"Role 이미 존재함: {name} (namespace: {namespace})")
            return existing

        # PolicyRule 객체 리스트 생성
        policy_rules = [
            V1PolicyRule(
                api_groups=rule.get("apiGroups", [""]),
                resources=rule.get("resources", []),
                verbs=rule.get("verbs", []),
                resource_names=rule.get("resourceNames"),
            )
            for rule in rules
        ]

        # Role 객체 생성
        role = V1Role(
            api_version="rbac.authorization.k8s.io/v1",
            kind="Role",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {},
                annotations=annotations or {},
            ),
            rules=policy_rules,
        )

        try:
            created_role = await self.k8s_client.rbac_v1.create_namespaced_role(
                namespace=namespace,
                body=role,
            )
            self.logger.info(f"Role 생성 완료: {name} (namespace: {namespace})")
            return created_role

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(f"Role 생성 충돌 (409), 재조회: {name}")
                existing = await self.get_role(name, namespace)
                if existing:
                    return existing

            self.logger.error(f"Role 생성 실패: {name} - {e.reason}")
            raise RoleCreationException(
                role_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"Role 생성 중 예외 발생: {name} - {str(e)}")
            raise RoleCreationException(
                role_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_role(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1Role]:
        """Role 비동기 조회

        Args:
            name: Role 이름
            namespace: 네임스페이스

        Returns:
            V1Role 객체 또는 None (존재하지 않으면)

        Raises:
            RoleReadException: 조회 실패 시 (404 제외)
        """
        try:
            role = await self.k8s_client.rbac_v1.read_namespaced_role(
                name=name,
                namespace=namespace,
            )
            return role

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.error(f"Role 조회 실패: {name} (namespace: {namespace}) - {e.reason}")
            raise RoleReadException(
                role_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"Role 조회 중 예외 발생: {name} - {str(e)}")
            raise RoleReadException(
                role_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_role(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """Role 비동기 삭제

        Args:
            name: Role 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            RoleDeletionException: 삭제 실패 시
        """
        self.logger.info(f"Role 삭제 시도: {name} (namespace: {namespace})")

        # 존재 여부 확인
        existing = await self.get_role(name, namespace)
        if not existing:
            self.logger.warning(f"Role가 존재하지 않음: {name} (namespace: {namespace})")
            raise RoleDeletionException(
                role_name=name,
                namespace=namespace,
                reason="Role does not exist",
            )

        try:
            await self.k8s_client.rbac_v1.delete_namespaced_role(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(f"Role 삭제 완료: {name} (namespace: {namespace})")
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(f"Role 이미 삭제됨: {name} (namespace: {namespace})")
                return True

            self.logger.error(f"Role 삭제 실패: {name} - {e.reason}")
            raise RoleDeletionException(
                role_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"Role 삭제 중 예외 발생: {name} - {str(e)}")
            raise RoleDeletionException(
                role_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_roles(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1Role]:
        """Role 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app_deployment=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1Role 객체 리스트

        Raises:
            RoleListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.rbac_v1.list_namespaced_role(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.rbac_v1.list_role_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.error(f"Role 목록 조회 실패 (namespace: {namespace}) - {e.reason}")
            raise RoleListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"Role 목록 조회 중 예외 발생 - {str(e)}")
            raise RoleListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """Role 존재 여부 확인

        Args:
            name: Role 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        role = await self.get_role(name, namespace)
        return role is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1Role:
        """Role 레이블 업데이트

        Args:
            name: Role 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1Role 객체

        Raises:
            RoleUpdateException: 업데이트 실패 시
        """
        self.logger.info(f"Role 레이블 업데이트: {name} (namespace: {namespace})")

        # 존재 여부 확인
        existing = await self.get_role(name, namespace)
        if not existing:
            raise RoleUpdateException(
                role_name=name,
                namespace=namespace,
                reason="Role does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            role = await self.k8s_client.rbac_v1.patch_namespaced_role(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(f"Role 레이블 업데이트 완료: {name} (namespace: {namespace})")
            return role

        except ApiException as e:
            self.logger.error(f"Role 레이블 업데이트 실패: {name} - {e.reason}")
            raise RoleUpdateException(
                role_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"Role 레이블 업데이트 중 예외 발생: {name} - {str(e)}")
            raise RoleUpdateException(
                role_name=name,
                namespace=namespace,
                reason=str(e),
            )
