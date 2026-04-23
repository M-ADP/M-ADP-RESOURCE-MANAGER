from fastapi import Depends
from src.core.project import ProjectId
from src.api.v1.app.schemas.event_response import AppEventsResponse, EventInfo
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppSecurityEventsUseCase:
    """App 보안 관련 이벤트(최근 60초) 조회 UseCase"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        app_name: str,
        project_id: str,
        since_seconds: int = 60,
    ) -> AppEventsResponse:
        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        events = await self.app_deployment_repo.get_events(deployment, since_seconds=since_seconds)

        return AppEventsResponse(
            deployment_name=deployment.name,
            namespace=deployment.namespace,
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
