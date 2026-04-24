from fastapi import Depends

from src.core.project import ProjectId
from src.api.v1.app.schemas.security_response import AppPodKillResponse
from src.app.app_deployment.exceptions import DeploymentNotFoundException, PodNotFoundException
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppPodKillUseCase:
    """특정 Pod 강제 종료 UseCase"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        app_name: str,
        project_id: str,
        pod_name: str,
    ) -> AppPodKillResponse:
        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        killed = await self.app_deployment_repo.kill_pod(deployment, pod_name)
        if not killed:
            raise PodNotFoundException(pod_name=pod_name, deployment_name=app_name)

        return AppPodKillResponse(pod_name=pod_name, namespace=namespace)
