"""Service 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class ServiceCreationException(ResourceCreationException):
    """Service 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Service",
            resource_name=service_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ServiceReadException(ResourceReadException):
    """Service 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Service",
            resource_name=service_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ServiceUpdateException(ResourceUpdateException):
    """Service 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Service",
            resource_name=service_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ServiceDeletionException(ResourceDeletionException):
    """Service 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Service",
            resource_name=service_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ServiceListException(ResourceListException):
    """Service 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Service",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
