"""RoleBinding 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1RoleBinding,
    V1ObjectMeta,
    V1RoleRef,
    RbacV1Subject,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from core.logger import Logger, get_logger
from .exceptions import (
    RoleBindingCreationException,
    RoleBindingReadException,
    RoleBindingUpdateException,
    RoleBindingDeletionException,
    RoleBindingListException,
)


class RoleBindingManager:
    """RoleBinding 리소스를 관리하는 클래스

    Args:
        k8s_client: KubernetesClient 인스턴스
        logger: Logger 인스턴스 (선택적)
    """

    def __init__(
        self,
        k8s_client: KubernetesClient,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_rolebinding(
        self,
        name: str,
        namespace: str,
        role_name: str,
        subjects: List[Dict[str, str]],
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> V1RoleBinding:
        """RoleBinding 비동기 생성 (멱등성 보장)

        Args:
            name: RoleBinding 이름
            namespace: 네임스페이스
            role_name: 바인딩할 Role 이름
            subjects: 주체 리스트 (예: [{"kind": "ServiceAccount", "name": "my-sa", "namespace": "default"}])
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리

        Returns:
            생성되거나 기존에 존재하는 V1RoleBinding 객체

        Raises:
            RoleBindingCreationException: RoleBinding 생성 실패 시
        """
        self.logger.info(f"RoleBinding 생성 시도: {name} (namespace: {namespace})")

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_rolebinding(name, namespace)
        if existing:
            self.logger.info(f"RoleBinding 이미 존재함: {name} (namespace: {namespace})")
            return existing

        # RoleRef 생성
        role_ref = V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind="Role",
            name=role_name,
        )

        # Subject 객체 리스트 생성
        subject_list = [
            RbacV1Subject(
                kind=subject["kind"],
                name=subject["name"],
                namespace=subject.get("namespace"),
                api_group=subject.get("apiGroup"),
            )
            for subject in subjects
        ]

        # RoleBinding 객체 생성
        rolebinding = V1RoleBinding(
            api_version="rbac.authorization.k8s.io/v1",
            kind="RoleBinding",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {},
                annotations=annotations or {},
            ),
            role_ref=role_ref,
            subjects=subject_list,
        )

        try:
            created_rb = await self.k8s_client.rbac_v1.create_namespaced_role_binding(
                namespace=namespace,
                body=rolebinding,
            )
            self.logger.info(f"RoleBinding 생성 완료: {name} (namespace: {namespace})")
            return created_rb

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(f"RoleBinding 생성 충돌 (409), 재조회: {name}")
                existing = await self.get_rolebinding(name, namespace)
                if existing:
                    return existing

            self.logger.error(f"RoleBinding 생성 실패: {name} - {e.reason}")
            raise RoleBindingCreationException(
                rolebinding_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"RoleBinding 생성 중 예외 발생: {name} - {str(e)}")
            raise RoleBindingCreationException(
                rolebinding_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_rolebinding(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1RoleBinding]:
        """RoleBinding 비동기 조회

        Args:
            name: RoleBinding 이름
            namespace: 네임스페이스

        Returns:
            V1RoleBinding 객체 또는 None (존재하지 않으면)

        Raises:
            RoleBindingReadException: 조회 실패 시 (404 제외)
        """
        try:
            rb = await self.k8s_client.rbac_v1.read_namespaced_role_binding(
                name=name,
                namespace=namespace,
            )
            return rb

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.error(f"RoleBinding 조회 실패: {name} (namespace: {namespace}) - {e.reason}")
            raise RoleBindingReadException(
                rolebinding_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"RoleBinding 조회 중 예외 발생: {name} - {str(e)}")
            raise RoleBindingReadException(
                rolebinding_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_rolebinding(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """RoleBinding 비동기 삭제

        Args:
            name: RoleBinding 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            RoleBindingDeletionException: 삭제 실패 시
        """
        self.logger.info(f"RoleBinding 삭제 시도: {name} (namespace: {namespace})")

        # 존재 여부 확인
        existing = await self.get_rolebinding(name, namespace)
        if not existing:
            self.logger.warning(f"RoleBinding가 존재하지 않음: {name} (namespace: {namespace})")
            raise RoleBindingDeletionException(
                rolebinding_name=name,
                namespace=namespace,
                reason="RoleBinding does not exist",
            )

        try:
            await self.k8s_client.rbac_v1.delete_namespaced_role_binding(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(f"RoleBinding 삭제 완료: {name} (namespace: {namespace})")
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(f"RoleBinding 이미 삭제됨: {name} (namespace: {namespace})")
                return True

            self.logger.error(f"RoleBinding 삭제 실패: {name} - {e.reason}")
            raise RoleBindingDeletionException(
                rolebinding_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"RoleBinding 삭제 중 예외 발생: {name} - {str(e)}")
            raise RoleBindingDeletionException(
                rolebinding_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_rolebindings(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1RoleBinding]:
        """RoleBinding 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1RoleBinding 객체 리스트

        Raises:
            RoleBindingListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.rbac_v1.list_namespaced_role_binding(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.rbac_v1.list_role_binding_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.error(f"RoleBinding 목록 조회 실패 (namespace: {namespace}) - {e.reason}")
            raise RoleBindingListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"RoleBinding 목록 조회 중 예외 발생 - {str(e)}")
            raise RoleBindingListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """RoleBinding 존재 여부 확인

        Args:
            name: RoleBinding 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        rb = await self.get_rolebinding(name, namespace)
        return rb is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1RoleBinding:
        """RoleBinding 레이블 업데이트

        Args:
            name: RoleBinding 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1RoleBinding 객체

        Raises:
            RoleBindingUpdateException: 업데이트 실패 시
        """
        self.logger.info(f"RoleBinding 레이블 업데이트: {name} (namespace: {namespace})")

        # 존재 여부 확인
        existing = await self.get_rolebinding(name, namespace)
        if not existing:
            raise RoleBindingUpdateException(
                rolebinding_name=name,
                namespace=namespace,
                reason="RoleBinding does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            rb = await self.k8s_client.rbac_v1.patch_namespaced_role_binding(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(f"RoleBinding 레이블 업데이트 완료: {name} (namespace: {namespace})")
            return rb

        except ApiException as e:
            self.logger.error(f"RoleBinding 레이블 업데이트 실패: {name} - {e.reason}")
            raise RoleBindingUpdateException(
                rolebinding_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"RoleBinding 레이블 업데이트 중 예외 발생: {name} - {str(e)}")
            raise RoleBindingUpdateException(
                rolebinding_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def add_subject(
        self,
        name: str,
        namespace: str,
        subject: Dict[str, str],
    ) -> V1RoleBinding:
        """RoleBinding에 Subject 추가

        Args:
            name: RoleBinding 이름
            namespace: 네임스페이스
            subject: 추가할 Subject (예: {"kind": "ServiceAccount", "name": "my-sa", "namespace": "default"})

        Returns:
            업데이트된 V1RoleBinding 객체

        Raises:
            RoleBindingUpdateException: 업데이트 실패 시
        """
        self.logger.info(f"RoleBinding에 Subject 추가: {name} (subject: {subject['name']})")

        # 존재 여부 확인
        existing = await self.get_rolebinding(name, namespace)
        if not existing:
            raise RoleBindingUpdateException(
                rolebinding_name=name,
                namespace=namespace,
                reason="RoleBinding does not exist",
            )

        # 기존 subjects 가져오기
        subjects = existing.subjects or []

        # 이미 존재하는지 확인
        for s in subjects:
            if s.kind == subject["kind"] and s.name == subject["name"]:
                if s.namespace == subject.get("namespace"):
                    self.logger.info(f"Subject 이미 존재함: {subject['name']}")
                    return existing

        # 새로운 Subject 추가
        subjects.append(
            RbacV1Subject(
                kind=subject["kind"],
                name=subject["name"],
                namespace=subject.get("namespace"),
                api_group=subject.get("apiGroup"),
            )
        )

        # Patch 요청
        body = {
            "subjects": [
                {
                    "kind": s.kind,
                    "name": s.name,
                    "namespace": s.namespace,
                    "apiGroup": s.api_group,
                }
                for s in subjects
            ]
        }

        try:
            rb = await self.k8s_client.rbac_v1.patch_namespaced_role_binding(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(f"Subject 추가 완료: {subject['name']} → {name}")
            return rb

        except ApiException as e:
            self.logger.error(f"Subject 추가 실패: {name} - {e.reason}")
            raise RoleBindingUpdateException(
                rolebinding_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"Subject 추가 중 예외 발생: {name} - {str(e)}")
            raise RoleBindingUpdateException(
                rolebinding_name=name,
                namespace=namespace,
                reason=str(e),
            )
