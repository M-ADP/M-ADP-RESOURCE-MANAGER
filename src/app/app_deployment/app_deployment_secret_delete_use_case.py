"""App Deployment Secret 삭제 Use Case"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.response import SecretDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentSecretDeleteUseCase(BaseUseCase):
    """App Deployment Secret 삭제 Use Case"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        project_id: str,
        app_name: str,
        secret_name: str,
    ) -> SecretDeleteResponse:
        """App Secret 삭제 및 Vault 접근 구조 정리"""

        namespace = ProjectId(project_id).namespace

        # 1. Deployment 조회
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(app_name, namespace)

        # 2. Secret 삭제 + 마지막 secret이면 Policy/Role 자동 정리
        # all_cleaned: 마지막 secret이어서 Policy/Role까지 정리된 경우 True
        all_cleaned = await self.app_deployment_repo.revoke_secret(deployment, secret_name)

        mount_point = self.app_deployment_repo.secret_mount_point

        return SecretDeleteResponse(
            name=secret_name,
            path=f"{mount_point}/data/{deployment.vault_secret_path(secret_name)}",
            all_secrets_deleted=all_cleaned,
        )
