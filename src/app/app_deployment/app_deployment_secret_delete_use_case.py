"""App Deployment Secret 삭제 Use Case"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.response import SecretKeyDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.common.util import NameConverter
from src.app.app_deployment.exceptions import DeploymentNotFoundException, SecretKeyNotFoundException
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentSecretDeleteUseCase(BaseUseCase):
    """App Deployment Secret 키 단위 삭제 Use Case"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(
            get_app_deployment_repository
        ),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        project_id: str,
        app_name: str,
        key: str,
    ) -> SecretKeyDeleteResponse:
        """Secret에서 특정 키만 제거"""

        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(app_name, namespace)

        removed = await self.app_deployment_repo.remove_secret_entry(deployment, key)
        if not removed:
            raise SecretKeyNotFoundException(key)

        mount_point = self.app_deployment_repo.secret_mount_point
        secret_path = deployment.vault_secret_path(deployment.vault_secret_name)

        return SecretKeyDeleteResponse(
            path=f"{mount_point}/data/{secret_path}",
            key=key,
        )
