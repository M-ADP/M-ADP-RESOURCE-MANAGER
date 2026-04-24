"""App Deployment 이미지 변경 Use Case"""

from fastapi import Depends

from src.api.v1.app.schemas.request import AppImageUpdateRequest
from src.api.v1.app.schemas.response import AppImageUpdateResponse, ContainerInfo
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.app.base_use_case import BaseUseCase
from src.common.config.harbor import HarborConfig
from src.common.util import NameConverter
from src.core.app_deployment import AppContainer, AppDeploymentRepository
from src.core.kubernetes.deployment import Container, Deployment
from src.core.project import ProjectId
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentImageUpdateUseCase(BaseUseCase):
    """App Deployment 이미지 변경 Use Case"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo
        self._harbor = HarborConfig()

    async def __call__(
        self,
        project_id: str,
        app_name: str,
        payload: AppImageUpdateRequest,
    ) -> AppImageUpdateResponse:
        namespace = ProjectId(project_id).namespace
        k8s_name = NameConverter.to_k8s_name(app_name)

        existing = await self.app_deployment_repo.find_deployment(k8s_name, namespace)
        if not existing:
            raise DeploymentNotFoundException(k8s_name, namespace)

        containers = [
            Container(
                name=spec.name,
                image=AppContainer(
                    name=spec.name,
                    image=spec.image,
                    harbor_url=self._harbor.url,
                ).full_image,
            )
            for spec in payload.containers
        ]

        deployment = Deployment(
            name=k8s_name,
            namespace=namespace,
            containers=containers,
            image_pull_secrets=[self._harbor.pull_secret_name],
        )

        updated = await self.app_deployment_repo.deploy(deployment)

        return AppImageUpdateResponse(
            name=updated.name,
            namespace=updated.namespace,
            containers=[ContainerInfo(name=c.name, image=c.image) for c in updated.containers],
        )
