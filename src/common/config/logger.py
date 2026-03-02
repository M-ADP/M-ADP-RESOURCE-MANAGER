from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggerConfig(BaseSettings):
    """로거 설정"""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

    # 로그 레벨
    log_level: str = "INFO"

    # 로그 포맷
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 날짜 포맷
    log_date_format: str = "%Y-%m-%d %H:%M:%S"

    # 로거 이름
    logger_name: str = "app_deployment"

    # 파일 로그 사용 여부
    enable_file_logging: bool = False

    # 로그 파일 경로
    log_file_path: Optional[str] = None