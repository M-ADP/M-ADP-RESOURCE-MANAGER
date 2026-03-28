"""App Deployment 로그 조회 UseCase"""

from typing import Optional

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.log_response import AppLogsResponse, PodLogInfo
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentLogsUseCase:
    """App Deployment 로그 조회 UseCase"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        app_name: str,
        project_id: str,
        tail_lines: Optional[int] = 100,
        since_seconds: Optional[int] = None,
        timestamps: bool = False,
    ) -> AppLogsResponse:
        """App 로그 조회"""

        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        # 1. Deployment 조회
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        # 2. Pod 목록 조회 (deployment 객체 전달)
        pods = await self.app_deployment_repo.get_pods(deployment)

        # 3. 각 Pod 로그 수집
        pod_logs = []
        for pod in pods:
            logs = await self.app_deployment_repo.get_pod_logs(
                pod_name=pod.name,
                namespace=deployment.namespace,
                tail_lines=tail_lines,
                since_seconds=since_seconds,
                timestamps=timestamps,
            )
            pod_logs.append(PodLogInfo(
                pod_name=pod.name,
                logs=logs.logs if logs else "",
            ))

        return AppLogsResponse(
            deployment_name=deployment.name,
            namespace=deployment.namespace,
            pod_logs=pod_logs,
        )
