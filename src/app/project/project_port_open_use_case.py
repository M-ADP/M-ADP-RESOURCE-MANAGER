from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectPortOpenRequest
from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_gateway_repository
from src.core.kubernetes.gateway import Gateway, GatewayRepository


class ProjectPortOpenUseCase(BaseUseCase):

    def __init__(
            self,
            gateway_repo: GatewayRepository = Depends(get_gateway_repository),
    ):
        self.gateway_repo = gateway_repo

    async def __call__(
            self,
            project_name: str,
            payload: ProjectPortOpenRequest
    ):
        """Project 포트 개방 (Gateway 생성)"""
        gateway = Gateway.for_project_port(
            project_name=project_name,
            port=payload.port,
            protocol=payload.protocol,
        )
        
        saved_gateway = await self.gateway_repo.save(gateway)

        return saved_gateway
