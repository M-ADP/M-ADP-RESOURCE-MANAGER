from typing import Optional
from src.infra.jenkins.client import JenkinsClient

_jenkins_client_instance: Optional[JenkinsClient] = None


def get_jenkins_client() -> JenkinsClient:
    """Jenkins 클라이언트 인스턴스 반환 (FastAPI Dependency용)"""
    global _jenkins_client_instance

    if _jenkins_client_instance is None:
        from src.common.config.jenkins import JenkinsConfig
        from src.core.logger import get_logger

        config = JenkinsConfig()
        logger = get_logger()
        _jenkins_client_instance = JenkinsClient(config, logger)

    return _jenkins_client_instance
