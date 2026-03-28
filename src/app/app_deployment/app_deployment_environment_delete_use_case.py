"""App Deployment Environment 삭제 Use Case (ConfigMap 삭제)"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.response import EnvironmentDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.common.util import NameConverter
from src.app.app_deployment.exceptions import DeploymentNotFoundException, ConfigMapNotFoundException
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentEnvironmentDeleteUseCase(BaseUseCase):
    """App Deployment Environment 삭제 Use Case (ConfigMap 삭제)"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        project_id: str,
        app_name: str,
    ) -> EnvironmentDeleteResponse:
        """App Environment 삭제"""

        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        # 1. Deployment 조회
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(app_name, namespace)

        # 2. 환경변수 존재 확인 (env_configmap_name 자동 활용)
        existing = await self.app_deployment_repo.get_env(deployment)
        if not existing:
            raise ConfigMapNotFoundException(deployment.env_configmap_name, namespace)

        # 3. 환경변수 삭제
        await self.app_deployment_repo.clear_env(deployment)

        return EnvironmentDeleteResponse(
            name=deployment.env_configmap_name,
            namespace=namespace,
            app_name=app_name,
            deleted=True,
        )
