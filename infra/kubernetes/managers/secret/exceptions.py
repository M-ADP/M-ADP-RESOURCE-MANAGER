"""Secret 접근 관리 관련 예외 클래스 정의"""

from typing import Optional


class SecretAccessException(Exception):
    """Secret 접근 관리 기본 예외"""

    def __init__(self, message: str, detail: Optional[dict] = None):
        self.message = message
        self.detail = detail or {}
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (detail: {self.detail})"


class SecretAccessBindingException(SecretAccessException):
    """Secret 접근 바인딩 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_account_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        message = (
            f"Secret 접근 바인딩 실패 [{namespace}/{service_account_name}]: {reason}"
        )
        super().__init__(message, detail)


class SecretAccessUnbindingException(SecretAccessException):
    """Secret 접근 바인딩 해제 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_account_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        message = (
            f"Secret 접근 바인딩 해제 실패 [{namespace}/{service_account_name}]: {reason}"
        )
        super().__init__(message, detail)


class VaultInjectionException(SecretAccessException):
    """Workload에 Vault 설정 주입 실패 시 발생하는 예외"""

    def __init__(
        self,
        workload_name: str,
        workload_type: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        message = (
            f"Vault 설정 주입 실패 [{workload_type}/{namespace}/{workload_name}]: {reason}"
        )
        super().__init__(message, detail)
