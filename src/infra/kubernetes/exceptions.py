"""Kubernetes 리소스 관리 관련 예외 클래스"""

from typing import Optional
from src.core import MadpException


class KubernetesResourceException(MadpException):
    """Kubernetes 리소스 관련 기본 예외"""

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_name: str,
        status_code: int = 500,
        detail: Optional[dict] = None
    ):
        """
        Args:
            message: 예외 메시지
            resource_type: 리소스 타입 (예: "Namespace", "ServiceAccount")
            resource_name: 리소스 이름
            status_code: HTTP 상태 코드
            detail: 추가 상세 정보
        """
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.status_code = status_code

        enhanced_detail = detail or {}
        enhanced_detail.update({
            "resource_type": resource_type,
            "resource_name": resource_name
        })
        self.extra_detail = enhanced_detail

        super().__init__(
            detail=f"[{resource_type}/{resource_name}] {message}"
        )


class ResourceNotFoundException(KubernetesResourceException):
    """리소스를 찾을 수 없을 때 발생하는 예외"""

    def __init__(
        self,
        resource_type: str,
        resource_name: str,
        namespace: Optional[str] = None,
        detail: Optional[dict] = None
    ):
        """
        Args:
            resource_type: 리소스 타입
            resource_name: 리소스 이름
            namespace: 네임스페이스 (선택적)
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        if namespace:
            enhanced_detail["namespace"] = namespace

        location = f"namespace '{namespace}'" if namespace else "클러스터"
        message = f"{location}에서 리소스를 찾을 수 없습니다"

        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_name=resource_name,
            status_code=404,
            detail=enhanced_detail
        )


class ResourceAlreadyExistsException(KubernetesResourceException):
    """리소스가 이미 존재할 때 발생하는 예외"""

    def __init__(
        self,
        resource_type: str,
        resource_name: str,
        namespace: Optional[str] = None,
        detail: Optional[dict] = None
    ):
        """
        Args:
            resource_type: 리소스 타입
            resource_name: 리소스 이름
            namespace: 네임스페이스 (선택적)
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        if namespace:
            enhanced_detail["namespace"] = namespace

        location = f"namespace '{namespace}'" if namespace else "클러스터"
        message = f"{location}에 리소스가 이미 존재합니다"

        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_name=resource_name,
            status_code=409,
            detail=enhanced_detail
        )


class ResourceCreationException(KubernetesResourceException):
    """리소스 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        resource_type: str,
        resource_name: str,
        reason: str,
        namespace: Optional[str] = None,
        detail: Optional[dict] = None
    ):
        """
        Args:
            resource_type: 리소스 타입
            resource_name: 리소스 이름
            reason: 실패 이유
            namespace: 네임스페이스 (선택적)
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        enhanced_detail["reason"] = reason
        if namespace:
            enhanced_detail["namespace"] = namespace

        message = f"리소스 생성 실패: {reason}"

        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_name=resource_name,
            status_code=500,
            detail=enhanced_detail
        )


class ResourceDeletionException(KubernetesResourceException):
    """리소스 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        resource_type: str,
        resource_name: str,
        reason: str,
        namespace: Optional[str] = None,
        detail: Optional[dict] = None
    ):
        """
        Args:
            resource_type: 리소스 타입
            resource_name: 리소스 이름
            reason: 실패 이유
            namespace: 네임스페이스 (선택적)
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        enhanced_detail["reason"] = reason
        if namespace:
            enhanced_detail["namespace"] = namespace

        message = f"리소스 삭제 실패: {reason}"

        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_name=resource_name,
            status_code=500,
            detail=enhanced_detail
        )


class ResourceUpdateException(KubernetesResourceException):
    """리소스 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        resource_type: str,
        resource_name: str,
        reason: str,
        namespace: Optional[str] = None,
        detail: Optional[dict] = None
    ):
        """
        Args:
            resource_type: 리소스 타입
            resource_name: 리소스 이름
            reason: 실패 이유
            namespace: 네임스페이스 (선택적)
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        enhanced_detail["reason"] = reason
        if namespace:
            enhanced_detail["namespace"] = namespace

        message = f"리소스 업데이트 실패: {reason}"

        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_name=resource_name,
            status_code=500,
            detail=enhanced_detail
        )


class ResourceReadException(KubernetesResourceException):
    """리소스 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        resource_type: str,
        resource_name: str,
        reason: str,
        namespace: Optional[str] = None,
        detail: Optional[dict] = None
    ):
        """
        Args:
            resource_type: 리소스 타입
            resource_name: 리소스 이름
            reason: 실패 이유
            namespace: 네임스페이스 (선택적)
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        enhanced_detail["reason"] = reason
        if namespace:
            enhanced_detail["namespace"] = namespace

        message = f"리소스 조회 실패: {reason}"

        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_name=resource_name,
            status_code=500,
            detail=enhanced_detail
        )


class ResourceListException(KubernetesResourceException):
    """리소스 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        resource_type: str,
        reason: str,
        namespace: Optional[str] = None,
        detail: Optional[dict] = None
    ):
        """
        Args:
            resource_type: 리소스 타입
            reason: 실패 이유
            namespace: 네임스페이스 (선택적)
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        enhanced_detail["reason"] = reason
        if namespace:
            enhanced_detail["namespace"] = namespace

        message = f"리소스 목록 조회 실패: {reason}"

        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_name="",  # 목록 조회는 특정 리소스명이 없음
            status_code=500,
            detail=enhanced_detail
        )


class KubernetesApiException(KubernetesResourceException):
    """Kubernetes API 호출 실패 시 발생하는 예외"""

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_name: str,
        api_status_code: int,
        api_reason: Optional[str] = None,
        detail: Optional[dict] = None
    ):
        """
        Args:
            message: 예외 메시지
            resource_type: 리소스 타입
            resource_name: 리소스 이름
            api_status_code: Kubernetes API 상태 코드
            api_reason: Kubernetes API 실패 이유
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        enhanced_detail["api_status_code"] = api_status_code
        if api_reason:
            enhanced_detail["api_reason"] = api_reason

        # API 상태 코드에 따라 HTTP 상태 코드 매핑
        http_status_map = {
            400: 400,  # Bad Request
            401: 401,  # Unauthorized
            403: 403,  # Forbidden
            404: 404,  # Not Found
            409: 409,  # Conflict
            422: 422,  # Unprocessable Entity
            500: 500,  # Internal Server Error
            503: 503,  # Service Unavailable
        }
        http_status_code = http_status_map.get(api_status_code, 500)

        super().__init__(
            message=f"Kubernetes API 호출 실패: {message}",
            resource_type=resource_type,
            resource_name=resource_name,
            status_code=http_status_code,
            detail=enhanced_detail
        )


class ResourceValidationException(KubernetesResourceException):
    """리소스 유효성 검증 실패 시 발생하는 예외"""

    def __init__(
        self,
        resource_type: str,
        resource_name: str,
        validation_errors: list[str],
        detail: Optional[dict] = None
    ):
        """
        Args:
            resource_type: 리소스 타입
            resource_name: 리소스 이름
            validation_errors: 유효성 검증 오류 목록
            detail: 추가 상세 정보
        """
        enhanced_detail = detail or {}
        enhanced_detail["validation_errors"] = validation_errors

        errors_str = ", ".join(validation_errors)
        message = f"리소스 유효성 검증 실패: {errors_str}"

        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_name=resource_name,
            status_code=422,
            detail=enhanced_detail
        )
