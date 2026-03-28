"""App Deployment Secret 생성 Use Case"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.request import SecretCreateRequest
from src.api.v1.app.schemas.response import SecretCreateResponse
from src.app.base_use_case import BaseUseCase
from src.common.util import NameConverter
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentSecretCreateUseCase(BaseUseCase):
    """App Deployment Secret 생성 Use Case"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        project_id: str,
        app_name: str,
        payload: SecretCreateRequest,
    ) -> SecretCreateResponse:
        """App Secret 저장 및 Vault 접근 구조 설정"""

        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        # 1. Deployment 조회
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(app_name, namespace)

        # 2. Secret 저장 + Policy + Role 설정 (deployment 프로퍼티 자동 활용)
        secret_path = await self.app_deployment_repo.store_secret(
            deployment=deployment,
            secret_name=payload.name,
            data=payload.data,
        )

        return SecretCreateResponse(
            name=payload.name,
            namespace=namespace,
            app_name=app_name,
            path=secret_path,
            policy_name=deployment.vault_policy_name,
            role_name=deployment.vault_role_name,
        )
