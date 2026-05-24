from pydantic_settings import BaseSettings, SettingsConfigDict


class AppDeploymentConfig(BaseSettings):
    """App Deployment 리소스 기본값 설정"""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

    default_cpu_limit: str = "500m"
    default_memory_limit: str = "2Gi"
    min_cpu_request: str = "100m"
    min_memory_request: str = "128Mi"
