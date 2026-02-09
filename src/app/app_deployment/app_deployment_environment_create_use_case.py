"""App Deployment Environment 생성 Use Case (ConfigMap 생성)"""

from fastapi import Depends

from src.api.v1.app.schemas.request import EnvironmentCreateRequest
from src.api.v1.app.schemas.response import EnvironmentCreateResponse
from src.app.base_use_case import BaseUseCase
from src.dependencies.kubernetes import get_deployment_repository, get_configmap_manager
from src.infra.kubernetes.managers.configmap import ConfigMapManager
from src.app.app_deployment.exceptions import DeploymentNotFoundException


class AppDeploymentEnvironmentCreateUseCase(BaseUseCase):
    """App Deployment Environment 생성 Use Case (ConfigMap 생성)"""

    def __init__(
        self,
        configmap_manager: ConfigMapManager = Depends(get_configmap_manager),
        deployment_repository=Depends(get_deployment_repository),
    ):
        self.configmap_manager = configmap_manager
        self.deployment_repository = deployment_repository

    async def __call__(
        self,
        namespace: str,
        app_name: str,
        payload: EnvironmentCreateRequest,
        user_id: str
    ) -> EnvironmentCreateResponse:
        """App Environment 생성 (ConfigMap 생성)

        Args:
            namespace: 네임스페이스 (프로젝트)
            app_name: App 이름 (Deployment 이름)
            payload: 환경 변수 데이터
            user_id: 사용자 ID

        Returns:
            EnvironmentCreateResponse: 생성된 ConfigMap 정보
        """

        # 1. Deployment 존재 확인
        deployment = await self.deployment_repository.find_by_name(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(app_name, namespace)

        # 2. ConfigMap 이름 결정 (App 이름 기반)
        configmap_name = f"{app_name}-env"

        # 3. ConfigMap 생성 또는 업데이트
        # 레이블에 app_deployment, managed-by 추가
        labels = {
            "app_deployment": app_name,
            "managed-by": "madp-resource-manager",
        }

        existing_configmap = await self.configmap_manager.get_configmap(
            name=configmap_name,
            namespace=namespace
        )

        if existing_configmap:
            # 기존 ConfigMap이 있으면 데이터 업데이트 (병합)
            await self.configmap_manager.update_data(
                name=configmap_name,
                namespace=namespace,
                data=payload.data,
                merge=True  # 기존 데이터와 병합
            )
        else:
            # 새로운 ConfigMap 생성
            await self.configmap_manager.create_configmap(
                name=configmap_name,
                namespace=namespace,
                data=payload.data,
                labels=labels,
            )

        return EnvironmentCreateResponse(
            name=configmap_name,
            namespace=namespace,
            app_name=app_name,
            data_keys=list(payload.data.keys())
        )
