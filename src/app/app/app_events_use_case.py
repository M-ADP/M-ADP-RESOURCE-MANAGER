"""App 이벤트 조회 UseCase"""

from fastapi import Depends

from src.api.v1.app.schemas.event_response import AppEventsResponse, EventInfo
from src.app.app.exceptions import DeploymentNotFoundException
from src.core.kubernetes.deployment import DeploymentRepository
from src.core.kubernetes.pod import PodRepository
from src.dependencies.kubernetes import get_deployment_repository, get_pod_repository


class AppEventsUseCase:
    """App(Deployment) 이벤트 조회 UseCase"""

    def __init__(
        self,
        deployment_repository: DeploymentRepository = Depends(get_deployment_repository),
        pod_repository: PodRepository = Depends(get_pod_repository),
    ):
        self.deployment_repository = deployment_repository
        self.pod_repository = pod_repository

    async def __call__(
        self,
        name: str,
        namespace: str,
    ) -> AppEventsResponse:
        """App 이벤트 조회

        Args:
            name: App(Deployment) 이름
            namespace: 네임스페이스

        Returns:
            AppEventsResponse: 이벤트 응답

        Raises:
            NotFoundException: Deployment가 존재하지 않는 경우
        """
        # 1. Deployment 존재 확인
        deployment = await self.deployment_repository.find_by_name(name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=name, namespace=namespace)

        # 2. 이벤트 조회
        events = await self.pod_repository.get_events_by_deployment(name, namespace)

        return AppEventsResponse(
            deployment_name=name,
            namespace=namespace,
            events=[
                EventInfo(
                    type=e.type,
                    reason=e.reason,
                    message=e.message,
                    involved_object_kind=e.involved_object_kind,
                    involved_object_name=e.involved_object_name,
                    first_timestamp=e.first_timestamp,
                    last_timestamp=e.last_timestamp,
                    count=e.count,
                )
                for e in events
            ],
        )
