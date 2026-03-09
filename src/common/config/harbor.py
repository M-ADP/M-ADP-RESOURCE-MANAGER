from pydantic_settings import BaseSettings, SettingsConfigDict


class HarborConfig(BaseSettings):
    """Harbor 컨테이너 레지스트리 설정

    자격증명(username/password)은 Vault에서 읽는다.
    이 설정은 Harbor URL, Vault 경로, K8s Secret 이름만 보유한다.
    """

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

    # Harbor 레지스트리 URL (e.g. harbor.example.com)
    url: str = "harbor.example.com"

    # Vault KV 경로 — {"username": "...", "password": "..."} 형태로 저장되어 있어야 함
    # e.g. secret/data/harbor/registry
    vault_secret_path: str = "harbor/registry"

    # Namespace에 생성될 docker-registry Secret 이름 (고정)
    pull_secret_name: str = "harbor-registry"
