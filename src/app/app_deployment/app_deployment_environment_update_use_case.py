"""App Deployment Environment 수정 Use Case (ConfigMap 수정)"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.request import EnvironmentUpdateRequest
from src.api.v1.app.schemas.response import EnvironmentUpdateResponse
from src.app.base_use_case import BaseUseCase
from src.common.util import NameConverter
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.common.const import DefaultLabel
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentEnvironmentUpdateUseCase(BaseUseCase):
    """App Deployment Environment 수정 Use Case (ConfigMap 수정)"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        project_id: str,
        app_name: str,
        payload: EnvironmentUpdateRequest,
    ) -> EnvironmentUpdateResponse:
        """App Environment 완전 교체"""

        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        # 1. Deployment 조회
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(app_name, namespace)

        # 2. 환경변수 upsert (없으면 생성, 있으면 완전 교체)
        existing = await self.app_deployment_repo.get_env(deployment)
        if existing:
            await self.app_deployment_repo.replace_env(deployment, payload.data)
        else:
            labels = {
                "app_deployment": deployment.name,
                **DefaultLabel.MANAGED_BY_LABEL,
            }
            await self.app_deployment_repo.set_env(deployment, payload.data, labels)

        return EnvironmentUpdateResponse(
            name=deployment.env_configmap_name,
            namespace=namespace,
            app_name=app_name,
            data_keys=list(payload.data.keys())
        )
