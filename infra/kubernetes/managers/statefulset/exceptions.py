"""StatefulSet 관리 관련 예외 클래스 정의"""

from typing import Optional
from infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class StatefulSetCreationException(ResourceCreationException):
    """StatefulSet 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        statefulset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StatefulSet",
            resource_name=statefulset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class StatefulSetReadException(ResourceReadException):
    """StatefulSet 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        statefulset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StatefulSet",
            resource_name=statefulset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class StatefulSetUpdateException(ResourceUpdateException):
    """StatefulSet 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        statefulset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StatefulSet",
            resource_name=statefulset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class StatefulSetDeletionException(ResourceDeletionException):
    """StatefulSet 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        statefulset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StatefulSet",
            resource_name=statefulset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class StatefulSetListException(ResourceListException):
    """StatefulSet 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StatefulSet",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
