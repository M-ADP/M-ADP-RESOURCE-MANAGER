"""App Deployment Restart Use Case"""

import datetime

from fastapi import Depends

from src.core.project import ProjectId
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.app.base_use_case import BaseUseCase
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import (
    get_app_deployment_repository,
    get_deployment_manager,
)
from src.infra.kubernetes.managers.deployment import DeploymentManager


class AppDeploymentRestartUseCase(BaseUseCase):
    """App Deployment Rollout Restart Use Case

    Deployment Pod 템플릿에 restartedAt 어노테이션을 패치하여
    kubectl rollout restart 와 동일한 롤링 재시작을 트리거합니다.
    """

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(
            get_app_deployment_repository
        ),
        deployment_manager: DeploymentManager = Depends(get_deployment_manager),
    ):
        self.app_deployment_repo = app_deployment_repo
        self.deployment_manager = deployment_manager

    async def __call__(
        self,
        app_name: str,
        project_id: str,
    ) -> dict:
        """App(Deployment) Rollout Restart

        Args:
            app_name: App 이름 (Deployment 이름)
            project_id: 프로젝트 ID

        Returns:
            재시작 결과 딕셔너리
        """
        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        # Deployment 존재 여부 확인
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        # Rollout Restart 트리거
        restarted_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        await self.deployment_manager.rollout_restart(
            name=app_name, namespace=namespace
        )

        return {
            "name": app_name,
            "namespace": namespace,
            "restarted_at": restarted_at,
        }
