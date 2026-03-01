"""ConfigMap 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class ConfigMapCreationException(ResourceCreationException):
    """ConfigMap 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        configmap_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ConfigMap",
            resource_name=configmap_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ConfigMapReadException(ResourceReadException):
    """ConfigMap 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        configmap_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ConfigMap",
            resource_name=configmap_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ConfigMapUpdateException(ResourceUpdateException):
    """ConfigMap 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        configmap_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ConfigMap",
            resource_name=configmap_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ConfigMapDeletionException(ResourceDeletionException):
    """ConfigMap 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        configmap_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ConfigMap",
            resource_name=configmap_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class ConfigMapListException(ResourceListException):
    """ConfigMap 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ConfigMap",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
