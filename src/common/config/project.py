from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectConfig(BaseSettings):
    """프로젝트 리소스 기본값 설정"""

    model_config = SettingsConfigDict(
        env_prefix="PROJECT_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

    default_cpu: str = "1"
    default_memory: str = "2Gi"
    default_disk: str = "32Mi"
    default_request_cpu: str = "100m"
    default_request_memory: str = "512Mi"
