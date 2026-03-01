"""ServiceAccount 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class ServiceAccountCreationException(ResourceCreationException):
    """ServiceAccount 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_account_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ServiceAccount",
            resource_name=service_account_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ServiceAccountReadException(ResourceReadException):
    """ServiceAccount 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_account_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ServiceAccount",
            resource_name=service_account_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ServiceAccountUpdateException(ResourceUpdateException):
    """ServiceAccount 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_account_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ServiceAccount",
            resource_name=service_account_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ServiceAccountDeletionException(ResourceDeletionException):
    """ServiceAccount 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_account_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ServiceAccount",
            resource_name=service_account_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ServiceAccountListException(ResourceListException):
    """ServiceAccount 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ServiceAccount",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
