"""App Deployment Environment 수정 Use Case (ConfigMap 수정)"""

from fastapi import Depends

from src.api.v1.app.schemas.request import EnvironmentUpdateRequest
from src.api.v1.app.schemas.response import EnvironmentUpdateResponse
from src.app.base_use_case import BaseUseCase
from src.dependencies.kubernetes import get_deployment_repository, get_configmap_manager
from src.infra.kubernetes.managers.configmap import ConfigMapManager
from src.app.app_deployment.exceptions import DeploymentNotFoundException, ConfigMapNotFoundException


class AppDeploymentEnvironmentUpdateUseCase(BaseUseCase):
    """App Deployment Environment 수정 Use Case (ConfigMap 수정)"""

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
        payload: EnvironmentUpdateRequest,
        user_id: str
    ) -> EnvironmentUpdateResponse:
        """App Environment 수정 (ConfigMap 데이터 교체)

        Args:
            namespace: 네임스페이스 (프로젝트)
            app_name: App 이름 (Deployment 이름)
            payload: 환경 변수 데이터
            user_id: 사용자 ID

        Returns:
            EnvironmentUpdateResponse: 수정된 ConfigMap 정보
        """

        # 1. Deployment 존재 확인
        deployment = await self.deployment_repository.find_by_name(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(app_name, namespace)

        # 2. ConfigMap 이름 결정 (App 이름 기반)
        configmap_name = f"{app_name}-env"

        # 3. ConfigMap 존재 확인
        existing_configmap = await self.configmap_manager.get_configmap(
            name=configmap_name,
            namespace=namespace
        )

        if not existing_configmap:
            raise ConfigMapNotFoundException(configmap_name, namespace)

        # 4. ConfigMap 데이터 교체 (merge=False로 완전 교체)
        await self.configmap_manager.update_data(
            name=configmap_name,
            namespace=namespace,
            data=payload.data,
            merge=False  # 기존 데이터 완전 교체
        )

        return EnvironmentUpdateResponse(
            name=configmap_name,
            namespace=namespace,
            app_name=app_name,
            data_keys=list(payload.data.keys())
        )
