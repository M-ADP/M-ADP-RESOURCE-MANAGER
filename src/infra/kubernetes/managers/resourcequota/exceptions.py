"""ResourceQuota 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class ResourceQuotaCreationException(ResourceCreationException):
    """ResourceQuota 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        resourcequota_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ResourceQuota",
            resource_name=resourcequota_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ResourceQuotaReadException(ResourceReadException):
    """ResourceQuota 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        resourcequota_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ResourceQuota",
            resource_name=resourcequota_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ResourceQuotaUpdateException(ResourceUpdateException):
    """ResourceQuota 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        resourcequota_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ResourceQuota",
            resource_name=resourcequota_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ResourceQuotaDeletionException(ResourceDeletionException):
    """ResourceQuota 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        resourcequota_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ResourceQuota",
            resource_name=resourcequota_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ResourceQuotaListException(ResourceListException):
    """ResourceQuota 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ResourceQuota",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
