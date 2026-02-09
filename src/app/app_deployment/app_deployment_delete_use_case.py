"""App Deployment 삭제 Use Case"""

from fastapi import Depends

from src.api.v1.app.schemas.response import AppDeleteResponse
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.app.base_use_case import BaseUseCase
from src.dependencies.kubernetes import get_deployment_repository, get_pvc_repository, get_service_account_repository


class AppDeploymentDeleteUseCase(BaseUseCase):
    """App Deployment 삭제 Use Case"""

    def __init__(
            self,
            deployment_repository=Depends(get_deployment_repository),
            pvc_repository=Depends(get_pvc_repository),
            service_account_repository=Depends(get_service_account_repository),
    ):
        self.deployment_repository = deployment_repository
        self.pvc_repository = pvc_repository
        self.service_account_repository = service_account_repository

    async def __call__(
            self,
            app_name: str,
            namespace: str,
            user_id: str
    ) -> AppDeleteResponse:
        """App(Deployment) 삭제 및 연관 리소스(PVC, SA) 삭제"""

        # 1. Deployment 조회하여 연관 PVC 확인
        deployment = await self.deployment_repository.find_by_name(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        pvc_names = []

        if deployment and deployment.volumes:
            for volume in deployment.volumes:
                if volume.pvc_name:
                    pvc_names.append(volume.pvc_name)

        # 2. Deployment 삭제
        deleted = await self.deployment_repository.delete(
            name=app_name,
            namespace=namespace,
        )

        # 3. ServiceAccount 삭제
        try:
            await self.service_account_repository.delete(
                name=f"{app_name}-sa",
                namespace=namespace,
            )
        except Exception:
            pass

        # 4. 연관 PVC 삭제
        for pvc_name in pvc_names:
            try:
                await self.pvc_repository.delete(
                    name=pvc_name,
                    namespace=namespace,
                )
            except Exception:
                # PVC 삭제 실패해도 Deployment는 이미 삭제됨
                pass

        return AppDeleteResponse(
            name=app_name,
            namespace=namespace,
            deleted=deleted,
        )
