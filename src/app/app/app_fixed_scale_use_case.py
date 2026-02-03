"""App Fixed Scale Use Case"""

from fastapi import Depends

from src.api.v1.app.schemas.request import FixedScaleRequest
from src.api.v1.app.schemas.response import FixedScaleResponse
from src.app.base_use_case import BaseUseCase
from src.app.app.exceptions import DeploymentNotFoundException
from src.dependencies.kubernetes import get_deployment_repository, get_hpa_repository


class AppFixedScaleUseCase(BaseUseCase):
    """App Fixed Scale (HPA 삭제 + 고정 레플리카) Use Case"""

    def __init__(
        self,
        deployment_repository=Depends(get_deployment_repository),
        hpa_repository=Depends(get_hpa_repository),
    ):
        self.deployment_repository = deployment_repository
        self.hpa_repository = hpa_repository

    async def __call__(
        self,
        name: str,
        namespace: str,
        payload: FixedScaleRequest,
        user_id: str,
    ) -> FixedScaleResponse:
        """App에 고정 레플리카 설정 (HPA 삭제)"""

        # 1. Deployment 존재 확인
        deployment = await self.deployment_repository.find_by_name(name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=name, namespace=namespace)

        # 2. HPA가 있으면 삭제
        hpa_name = f"{name}-hpa"
        hpa_deleted = await self.hpa_repository.delete(hpa_name, namespace)

        # 3. Deployment replicas 업데이트
        await self.deployment_repository.update_replicas(
            name=name,
            namespace=namespace,
            replicas=payload.replicas,
        )

        # 4. 최신 상태 조회
        updated_deployment = await self.deployment_repository.find_by_name(name, namespace)

        return FixedScaleResponse(
            name=updated_deployment.name,
            namespace=updated_deployment.namespace,
            replicas=updated_deployment.replicas,
            hpa_deleted=hpa_deleted,
        )
