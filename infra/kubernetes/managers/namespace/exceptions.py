"""Namespace 리소스 관련 예외 클래스"""

from typing import Optional

from infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceNotFoundException,
    ResourceDeletionException,
    ResourceUpdateException,
    KubernetesResourceException,
)


class NamespaceCreationException(ResourceCreationException):
    """Namespace 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace_name: str,
        reason: str,
        detail: Optional[dict] = None
    ):
        """
        Args:
            namespace_name: Namespace 이름
            reason: 실패 이유
            detail: 추가 상세 정보
        """
        super().__init__(
            resource_type="Namespace",
            resource_name=namespace_name,
            reason=reason,
            namespace=None,
            detail=detail
        )


class NamespaceNotFoundException(ResourceNotFoundException):
    """Namespace를 찾을 수 없을 때 발생하는 예외"""

    def __init__(
        self,
        namespace_name: str,
        detail: Optional[dict] = None
    ):
        """
        Args:
            namespace_name: Namespace 이름
            detail: 추가 상세 정보
        """
        super().__init__(
            resource_type="Namespace",
            resource_name=namespace_name,
            namespace=None,
            detail=detail
        )


class NamespaceDeletionException(ResourceDeletionException):
    """Namespace 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace_name: str,
        reason: str,
        detail: Optional[dict] = None
    ):
        """
        Args:
            namespace_name: Namespace 이름
            reason: 실패 이유
            detail: 추가 상세 정보
        """
        super().__init__(
            resource_type="Namespace",
            resource_name=namespace_name,
            reason=reason,
            namespace=None,
            detail=detail
        )


class NamespaceUpdateException(ResourceUpdateException):
    """Namespace 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace_name: str,
        reason: str,
        detail: Optional[dict] = None
    ):
        """
        Args:
            namespace_name: Namespace 이름
            reason: 실패 이유
            detail: 추가 상세 정보
        """
        super().__init__(
            resource_type="Namespace",
            resource_name=namespace_name,
            reason=reason,
            namespace=None,
            detail=detail
        )


class NamespaceReadException(KubernetesResourceException):
    """Namespace 조회 실패 시 발생하는 예외 (404 제외)"""

    def __init__(
        self,
        namespace_name: str,
        reason: str,
        api_status_code: int = 500,
        detail: Optional[dict] = None
    ):
        """
        Args:
            namespace_name: Namespace 이름
            reason: 실패 이유
            api_status_code: API 상태 코드
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        enhanced_detail["api_status_code"] = api_status_code

        # API 상태 코드에 따라 HTTP 상태 코드 매핑
        http_status_map = {
            400: 400, 401: 401, 403: 403, 500: 500, 503: 503
        }
        http_status_code = http_status_map.get(api_status_code, 500)

        super().__init__(
            message=f"조회 실패: {reason}",
            resource_type="Namespace",
            resource_name=namespace_name,
            status_code=http_status_code,
            detail=enhanced_detail
        )


class NamespaceListException(KubernetesResourceException):
    """Namespace 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        reason: str,
        api_status_code: int = 500,
        detail: Optional[dict] = None
    ):
        """
        Args:
            reason: 실패 이유
            api_status_code: API 상태 코드
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        enhanced_detail["api_status_code"] = api_status_code

        # API 상태 코드에 따라 HTTP 상태 코드 매핑
        http_status_map = {
            400: 400, 401: 401, 403: 403, 500: 500, 503: 503
        }
        http_status_code = http_status_map.get(api_status_code, 500)

        super().__init__(
            message=f"목록 조회 실패: {reason}",
            resource_type="Namespace",
            resource_name="*",
            status_code=http_status_code,
            detail=enhanced_detail
        )
