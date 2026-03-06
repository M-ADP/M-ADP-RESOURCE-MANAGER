"""PersistentVolumeClaim 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class PersistentVolumeClaimCreationException(ResourceCreationException):
    """PersistentVolumeClaim 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        pvc_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="PersistentVolumeClaim",
            resource_name=pvc_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class PersistentVolumeClaimReadException(ResourceReadException):
    """PersistentVolumeClaim 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        pvc_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="PersistentVolumeClaim",
            resource_name=pvc_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class PersistentVolumeClaimUpdateException(ResourceUpdateException):
    """PersistentVolumeClaim 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        pvc_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="PersistentVolumeClaim",
            resource_name=pvc_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class PersistentVolumeClaimDeletionException(ResourceDeletionException):
    """PersistentVolumeClaim 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        pvc_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="PersistentVolumeClaim",
            resource_name=pvc_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class PersistentVolumeClaimListException(ResourceListException):
    """PersistentVolumeClaim 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="PersistentVolumeClaim",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
