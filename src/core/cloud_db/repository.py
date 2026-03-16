"""CloudDb 도메인 Repository 인터페이스"""

from src.core.app_deployment.repository import AppDeploymentRepository


class CloudDbRepository(AppDeploymentRepository):
    """
    CloudDb 도메인 Repository.

    AppDeploymentRepository와 동일한 인터페이스를 사용하며,
    내부 구현에서 StatefulSet을 사용한다.
    """
