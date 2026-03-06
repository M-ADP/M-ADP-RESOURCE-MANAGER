"""RoleBinding 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class RoleBindingCreationException(ResourceCreationException):
    """RoleBinding 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        rolebinding_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="RoleBinding",
            resource_name=rolebinding_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class RoleBindingReadException(ResourceReadException):
    """RoleBinding 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        rolebinding_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="RoleBinding",
            resource_name=rolebinding_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class RoleBindingUpdateException(ResourceUpdateException):
    """RoleBinding 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        rolebinding_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="RoleBinding",
            resource_name=rolebinding_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class RoleBindingDeletionException(ResourceDeletionException):
    """RoleBinding 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        rolebinding_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="RoleBinding",
            resource_name=rolebinding_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class RoleBindingListException(ResourceListException):
    """RoleBinding 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="RoleBinding",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
