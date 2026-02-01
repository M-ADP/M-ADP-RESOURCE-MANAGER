"""App 삭제 Use Case"""

from fastapi import Depends

from src.api.v1.app.schemas.response import AppDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.dependencies.kubernetes import get_deployment_manager


class AppDeleteUseCase(BaseUseCase):
    """App(Deployment) 삭제 Use Case"""

    def __init__(
            self,
            deployment_manager=Depends(get_deployment_manager),
    ):
        self.deployment_manager = deployment_manager

    async def __call__(
            self,
            name: str,
            namespace: str,
            user_id: str
    ) -> AppDeleteResponse:
        """App(Deployment) 삭제"""

        # Deployment 삭제
        deleted = await self.deployment_manager.delete_deployment(
            name=name,
            namespace=namespace,
        )

        return AppDeleteResponse(
            name=name,
            namespace=namespace,
            deleted=deleted,
        )
