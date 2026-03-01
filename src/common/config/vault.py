from typing import Optional
from pydantic_settings import BaseSettings


class VaultConfig(BaseSettings):
    """Vault 클라이언트 설정"""

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

    class Config:
        env_prefix = "VAULT_"  # 환경변수 접두사: VAULT_ADDR, VAULT_TOKEN 등

VAULT_CONFIG = VaultConfig()