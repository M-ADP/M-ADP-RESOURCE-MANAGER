from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class VaultConfig(BaseSettings):
    """Vault 클라이언트 설정"""

    model_config = SettingsConfigDict(
        env_prefix="VAULT_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

    # Vault 서버 주소
    addr: str = "http://localhost:8200"

    # Vault 토큰 (Dev 모드 또는 직접 인증 시)
    token: Optional[str] = None

    # Vault Namespace (Enterprise 기능)
    namespace: Optional[str] = None

    # Kubernetes Auth Mount Path
    kubernetes_auth_path: str = "kubernetes"

    # KV Secret Engine Mount Point
    secret_mount_point: str = "secret"

    # API 타임아웃 (초)
    api_timeout: int = 30

    # 재시도 횟수
    max_retries: int = 3

VAULT_CONFIG = VaultConfig()