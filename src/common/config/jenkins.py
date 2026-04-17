from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class JenkinsConfig(BaseSettings):
    """Jenkins 클라이언트 설정"""

    model_config = SettingsConfigDict(
        env_prefix="JENKINS_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

    # Jenkins 서버 URL
    url: str = "http://jenkins-controller.madp.svc.cluster.local:8080"

    # Jenkins 사용자 이름
    user: Optional[str] = None

    # Jenkins API 토큰 또는 패스워드
    token: Optional[str] = None

    # 기본 파이프라인 Job 이름
    job_name: str = "app-deployment-pipeline"

    # API 타임아웃 (초)
    timeout: int = 30
