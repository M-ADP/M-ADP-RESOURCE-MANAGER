"""App 로그 조회 UseCase"""

from typing import Optional

from fastapi import Depends

from src.api.v1.app.schemas.log_response import AppLogsResponse, PodLogInfo
from src.app.app.exceptions import DeploymentNotFoundException
from src.core.kubernetes.deployment import DeploymentRepository
from src.core.kubernetes.pod import PodRepository
from src.dependencies.kubernetes import get_deployment_repository, get_pod_repository


class AppLogsUseCase:
    """App(Deployment) 로그 조회 UseCase"""

    def __init__(
        self,
        deployment_repository: DeploymentRepository = Depends(get_deployment_repository),
        pod_repository: PodRepository = Depends(get_pod_repository),
    ):
        self.deployment_repository = deployment_repository
        self.pod_repository = pod_repository

    async def __call__(
        self,
        app_name: str,
        namespace: str,
        tail_lines: Optional[int] = 100,
        since_seconds: Optional[int] = None,
        timestamps: bool = False,
    ) -> AppLogsResponse:
        """App 로그 조회

        Args:
            app_name: App(Deployment) 이름
            namespace: 네임스페이스
            tail_lines: 마지막 N줄만 조회
            since_seconds: 최근 N초 동안의 로그만 조회
            timestamps: 타임스탬프 포함 여부

        Returns:
            AppLogsResponse: 로그 응답

        Raises:
            NotFoundException: Deployment가 존재하지 않는 경우
        """
        # 1. Deployment 존재 확인
        deployment = await self.deployment_repository.find_by_name(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        # 2. Pod 목록 조회
        pods = await self.pod_repository.find_by_deployment(app_name, namespace)

        # 3. 각 Pod 로그 수집
        pod_logs = []
        for pod in pods:
            logs = await self.pod_repository.get_logs(
                pod_name=pod.name,
                namespace=namespace,
                tail_lines=tail_lines,
                since_seconds=since_seconds,
                timestamps=timestamps,
            )
            pod_logs.append(
                PodLogInfo(
                    pod_name=pod.name,
                    logs=logs.logs if logs else "",
                )
            )

        return AppLogsResponse(
            deployment_name=app_name,
            namespace=namespace,
            pod_logs=pod_logs,
        )
