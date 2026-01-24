from fastapi import Depends

from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_gateway_repository
from src.core.kubernetes.gateway import GatewayRepository


class ProjectPortCloseUseCase(BaseUseCase):

    def __init__(
            self,
            gateway_repo: GatewayRepository = Depends(get_gateway_repository),
    ):
        self.gateway_repo = gateway_repo

    async def __call__(
            self,
            project_name: str,
            port_id: int
    ) -> bool:
        """Project 포트 정리 (Gateway 리소스 정리)"""
        gateway_name = f"{project_name}-gateway"
        
        closed = await self.gateway_repo.delete(name=gateway_name, namespace=project_name)

        return closed
