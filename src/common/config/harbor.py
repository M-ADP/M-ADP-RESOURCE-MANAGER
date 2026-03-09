from pydantic_settings import BaseSettings, SettingsConfigDict


class HarborConfig(BaseSettings):
    """Harbor 컨테이너 레지스트리 설정 (Vault env 주입 기반)"""

    model_config = SettingsConfigDict(
        env_prefix="HARBOR_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

    url: str = "harbor.example.com"
    username: str
    password: str

    # Namespace에 생성될 docker-registry Secret 이름
    pull_secret_name: str = "harbor-registry"
