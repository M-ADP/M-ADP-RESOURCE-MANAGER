from fastapi import Depends

from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_service_repository
from src.core.kubernetes.service import ServiceRepository


class ProjectPortCloseUseCase(BaseUseCase):

    def __init__(
            self,
            service_repo: ServiceRepository = Depends(get_service_repository),
    ):
        self.service_repo = service_repo

    async def __call__(
            self,
            project_name: str,
            service_name: str
    ) -> bool:
        """Project 포트 정리 (Service 삭제)"""
        closed = await self.service_repo.delete(name=service_name, namespace=project_name)
        return closed
