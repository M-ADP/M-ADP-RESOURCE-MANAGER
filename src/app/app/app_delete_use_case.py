"""App 삭제 Use Case"""

from fastapi import Depends

from src.api.v1.app.schemas.response import AppDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.dependencies.kubernetes import get_deployment_manager, get_pvc_manager


class AppDeleteUseCase(BaseUseCase):
    """App(Deployment) 삭제 Use Case"""

    def __init__(
            self,
            deployment_manager=Depends(get_deployment_manager),
            pvc_manager=Depends(get_pvc_manager),
    ):
        self.deployment_manager = deployment_manager
        self.pvc_manager = pvc_manager

    async def __call__(
            self,
            name: str,
            namespace: str,
            user_id: str
    ) -> AppDeleteResponse:
        """App(Deployment) 삭제 및 연관 PVC 삭제"""

        # 1. Deployment 조회하여 연관 PVC 확인
        deployment = await self.deployment_manager.get_deployment(name, namespace)
        pvc_names = []

        if deployment and deployment.spec.template.spec.volumes:
            for volume in deployment.spec.template.spec.volumes:
                if volume.persistent_volume_claim:
                    pvc_names.append(volume.persistent_volume_claim.claim_name)

        # 2. Deployment 삭제
        deleted = await self.deployment_manager.delete_deployment(
            name=name,
            namespace=namespace,
        )

        # 3. 연관 PVC 삭제
        for pvc_name in pvc_names:
            try:
                await self.pvc_manager.delete_pvc(
                    name=pvc_name,
                    namespace=namespace,
                )
            except Exception:
                # PVC 삭제 실패해도 Deployment는 이미 삭제됨
                pass

        return AppDeleteResponse(
            name=name,
            namespace=namespace,
            deleted=deleted,
        )
