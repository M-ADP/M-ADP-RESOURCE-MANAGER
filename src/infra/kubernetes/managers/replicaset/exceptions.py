"""ReplicaSet 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class ReplicaSetCreationException(ResourceCreationException):
    """ReplicaSet 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        replicaset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ReplicaSet",
            resource_name=replicaset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ReplicaSetReadException(ResourceReadException):
    """ReplicaSet 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        replicaset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ReplicaSet",
            resource_name=replicaset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ReplicaSetUpdateException(ResourceUpdateException):
    """ReplicaSet 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        replicaset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ReplicaSet",
            resource_name=replicaset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ReplicaSetDeletionException(ResourceDeletionException):
    """ReplicaSet 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        replicaset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ReplicaSet",
            resource_name=replicaset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ReplicaSetListException(ResourceListException):
    """ReplicaSet 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ReplicaSet",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
