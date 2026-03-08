"""App Deployment Fixed Scale Use Case"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.request import FixedScaleRequest
from src.api.v1.app.schemas.response import FixedScaleResponse
from src.app.base_use_case import BaseUseCase
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentFixedScaleUseCase(BaseUseCase):
    """App Deployment Fixed Scale (HPA 삭제 + 고정 레플리카) Use Case"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        app_name: str,
        project_id: str,
        payload: FixedScaleRequest,
        user_id: str,
    ) -> FixedScaleResponse:
        """App에 고정 레플리카 설정 (HPA 비활성화)"""

        namespace = ProjectId(project_id).namespace

        # 1. Deployment 조회
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        # 2. 오토스케일 비활성화 (deployment.hpa_name 자동 활용)
        hpa_deleted = await self.app_deployment_repo.disable_autoscale(deployment)

        # 3. 고정 레플리카 수로 스케일
        updated_deployment = await self.app_deployment_repo.scale(deployment, payload.replicas)

        return FixedScaleResponse(
            name=updated_deployment.name,
            namespace=updated_deployment.namespace,
            replicas=updated_deployment.replicas,
            hpa_deleted=hpa_deleted,
        )
