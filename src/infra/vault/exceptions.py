"""Vault 관련 예외 클래스 정의"""

from typing import Optional


class VaultException(Exception):
    """Vault 관련 기본 예외"""

    def __init__(self, message: str, detail: Optional[dict] = None):
        self.message = message
        self.detail = detail or {}
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (detail: {self.detail})"


class VaultConnectionException(VaultException):
    """Vault 연결 실패 시 발생하는 예외"""

    def __init__(self, vault_addr: str, reason: str, detail: Optional[dict] = None):
        message = f"Vault 연결 실패: {vault_addr} - {reason}"
        super().__init__(message, detail)


class VaultAuthException(VaultException):
    """Vault 인증 실패 시 발생하는 예외"""

    def __init__(self, reason: str, detail: Optional[dict] = None):
        message = f"Vault 인증 실패: {reason}"
        super().__init__(message, detail)


class VaultRoleException(VaultException):
    """Vault Role 작업 실패 시 발생하는 예외"""

    def __init__(self, role_name: str, operation: str, reason: str, detail: Optional[dict] = None):
        message = f"Vault Role {operation} 실패 [{role_name}]: {reason}"
        super().__init__(message, detail)


class VaultPolicyException(VaultException):
    """Vault Policy 작업 실패 시 발생하는 예외"""

    def __init__(self, policy_name: str, operation: str, reason: str, detail: Optional[dict] = None):
        message = f"Vault Policy {operation} 실패 [{policy_name}]: {reason}"
        super().__init__(message, detail)


class VaultSecretException(VaultException):
    """Vault Secret 작업 실패 시 발생하는 예외"""

    def __init__(self, secret_path: str, operation: str, reason: str, detail: Optional[dict] = None):
        message = f"Vault Secret {operation} 실패 [{secret_path}]: {reason}"
        super().__init__(message, detail)
