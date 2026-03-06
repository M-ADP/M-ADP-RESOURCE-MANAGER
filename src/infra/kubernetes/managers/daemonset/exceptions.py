"""DaemonSet 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class DaemonSetCreationException(ResourceCreationException):
    """DaemonSet 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        daemonset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="DaemonSet",
            resource_name=daemonset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class DaemonSetReadException(ResourceReadException):
    """DaemonSet 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        daemonset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="DaemonSet",
            resource_name=daemonset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class DaemonSetUpdateException(ResourceUpdateException):
    """DaemonSet 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        daemonset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="DaemonSet",
            resource_name=daemonset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class DaemonSetDeletionException(ResourceDeletionException):
    """DaemonSet 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        daemonset_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="DaemonSet",
            resource_name=daemonset_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class DaemonSetListException(ResourceListException):
    """DaemonSet 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="DaemonSet",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
