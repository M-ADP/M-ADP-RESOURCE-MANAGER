"""StorageClass 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class StorageClassCreationException(ResourceCreationException):
    """StorageClass 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        sc_name: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StorageClass",
            resource_name=sc_name,
            reason=reason,
            namespace=None,
            detail=detail,
        )


class StorageClassReadException(ResourceReadException):
    """StorageClass 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        sc_name: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StorageClass",
            resource_name=sc_name,
            reason=reason,
            namespace=None,
            detail=detail,
        )


class StorageClassUpdateException(ResourceUpdateException):
    """StorageClass 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        sc_name: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StorageClass",
            resource_name=sc_name,
            reason=reason,
            namespace=None,
            detail=detail,
        )


class StorageClassDeletionException(ResourceDeletionException):
    """StorageClass 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        sc_name: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StorageClass",
            resource_name=sc_name,
            reason=reason,
            namespace=None,
            detail=detail,
        )


class StorageClassListException(ResourceListException):
    """StorageClass 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="StorageClass",
            reason=reason,
            namespace=None,
            detail=detail,
        )
