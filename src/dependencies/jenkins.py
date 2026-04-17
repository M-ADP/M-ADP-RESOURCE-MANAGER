from typing import Optional
from src.common.config.jenkins import JenkinsConfig
from src.infra.jenkins.client import JenkinsClient
from src.core.logger import get_logger, Logger

_jenkins_client_instance: Optional[JenkinsClient] = None


def get_jenkins_client(
    config: Optional[JenkinsConfig] = None, logger: Optional[Logger] = None
) -> JenkinsClient:
    """Jenkins 클라이언트 인스턴스 반환"""
    global _jenkins_client_instance

    if _jenkins_client_instance is None:
        cfg = config or JenkinsConfig()
        log = logger or get_logger()
        _jenkins_client_instance = JenkinsClient(cfg, log)

    return _jenkins_client_instance
