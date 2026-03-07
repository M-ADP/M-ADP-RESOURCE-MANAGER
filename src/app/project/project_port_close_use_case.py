from fastapi import Depends

from src.app.base_use_case import BaseUseCase
from src.core.project import ProjectRepository
from src.dependencies.kubernetes import get_project_repository


class ProjectPortCloseUseCase(BaseUseCase):

    def __init__(
            self,
            project_repo: ProjectRepository = Depends(get_project_repository),
    ):
        self.project_repo = project_repo

    async def __call__(
            self,
            project_name: str,
            service_name: str
    ) -> bool:
        """Project 포트 정리 (Service 삭제)"""
        return await self.project_repo.delete_service(id=service_name, namespace=f"project-{project_name}")
