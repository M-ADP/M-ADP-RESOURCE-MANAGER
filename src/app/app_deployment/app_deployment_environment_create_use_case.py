"""App Deployment Environment 생성 Use Case (ConfigMap 생성)"""

from fastapi import Depends

from src.api.v1.app.schemas.request import EnvironmentCreateRequest
from src.api.v1.app.schemas.response import EnvironmentCreateResponse
from src.app.base_use_case import BaseUseCase
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.common.const import DefaultLabel
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentEnvironmentCreateUseCase(BaseUseCase):
    """App Deployment Environment 생성 Use Case (ConfigMap 생성)"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        namespace: str,
        app_name: str,
        payload: EnvironmentCreateRequest,
        user_id: str
    ) -> EnvironmentCreateResponse:
        """App Environment 생성 (없으면 신규 생성, 있으면 병합)"""

        # 1. Deployment 조회
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(app_name, namespace)

        # 2. 환경변수 설정 (create-or-merge, env_configmap_name 자동 활용)
        labels = {
            "app_deployment": deployment.name,
            **DefaultLabel.MANAGED_BY_LABEL,
        }
        await self.app_deployment_repo.set_env(deployment, payload.data, labels)

        return EnvironmentCreateResponse(
            name=deployment.env_configmap_name,
            namespace=namespace,
            app_name=app_name,
            data_keys=list(payload.data.keys())
        )
