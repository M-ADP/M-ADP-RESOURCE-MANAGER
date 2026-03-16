"""App Deployment 삭제 Use Case"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.response import AppDeleteResponse
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.app.base_use_case import BaseUseCase
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository, get_service_manager
from src.infra.kubernetes.managers.service import ServiceManager


class AppDeploymentDeleteUseCase(BaseUseCase):
    """App Deployment 삭제 Use Case"""

    def __init__(
            self,
            app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
            service_manager: ServiceManager = Depends(get_service_manager),
    ):
        self.app_deployment_repo = app_deployment_repo
        self.service_manager = service_manager

    async def __call__(
            self,
            app_name: str,
            project_id: str,
    ) -> AppDeleteResponse:
        """App(Deployment) 삭제 및 연관 리소스(PVC, SA) 정리"""

        namespace = ProjectId(project_id).namespace

        # 1. Deployment 조회하여 연관 PVC 목록 확인
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        pvc_names = [v.pvc_name for v in deployment.volumes if v.pvc_name]

        # 2. Service 삭제 (존재하지 않아도 무시)
        try:
            await self.service_manager.delete_service(f"{app_name}-svc", namespace)
        except Exception:
            pass

        # 3. Deployment 제거
        deleted = await self.app_deployment_repo.undeploy(deployment)

        # 4. ID(ServiceAccount) 바인딩 해제 (deployment.sa_name 자동 활용)
        try:
            await self.app_deployment_repo.unbind_identity(deployment.sa_name, namespace)
        except Exception:
            pass

        # 5. 스토리지 해제
        for pvc_name in pvc_names:
            try:
                await self.app_deployment_repo.deprovision_storage(pvc_name, namespace)
            except Exception:
                pass

        return AppDeleteResponse(
            name=app_name,
            namespace=namespace,
            deleted=deleted,
        )
