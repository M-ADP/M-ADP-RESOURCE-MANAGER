"""App Deployment 로그 조회 UseCase"""

from typing import Optional

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.log_response import AppLogsResponse, PodLogInfo
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository

_PHASE_MESSAGES = {
    "Pending": "파드가 아직 시작되지 않았습니다",
    "Running": "로그가 없습니다",
    "Succeeded": "파드 실행이 완료되었습니다 (컨테이너 종료됨)",
    "Failed": "파드가 실패 상태입니다",
}


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

        if not pods:
            return AppLogsResponse(
                deployment_name=deployment.name,
                namespace=deployment.namespace,
                pod_logs=[],
                message="앱이 아직 시작되지 않았습니다",
            )

        # 3. 각 Pod 로그 수집
        main_container = deployment.containers[0].name if deployment.containers else None
        pod_logs = []
        for pod in pods:
            logs = await self.app_deployment_repo.get_pod_logs(
                pod_name=pod.name,
                namespace=deployment.namespace,
                container_name=main_container,
                tail_lines=tail_lines,
                since_seconds=since_seconds,
                timestamps=timestamps,
            )
            if logs:
                pod_logs.append(PodLogInfo(pod_name=pod.name, logs=logs.logs))
            else:
                msg = _PHASE_MESSAGES.get(pod.phase or "Pending", "로그를 조회할 수 없습니다")
                pod_logs.append(PodLogInfo(pod_name=pod.name, logs="", message=msg))

        return AppLogsResponse(
            deployment_name=deployment.name,
            namespace=deployment.namespace,
            pod_logs=pod_logs,
        )
