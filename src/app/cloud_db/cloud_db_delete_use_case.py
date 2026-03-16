"""Cloud DB 삭제 Use Case"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.cloud_db.schemas.response import CloudDbDeleteResponse
from src.app.cloud_db.exceptions import CloudDbNotFoundException
from src.app.base_use_case import BaseUseCase
from src.core.cloud_db import CloudDbRepository
from src.dependencies.kubernetes import get_cloud_db_repository, get_service_manager
from src.infra.kubernetes.managers.service import ServiceManager


class CloudDbDeleteUseCase(BaseUseCase):
    """Cloud DB 삭제 Use Case"""

    def __init__(
            self,
            cloud_db_repo: CloudDbRepository = Depends(get_cloud_db_repository),
            service_manager: ServiceManager = Depends(get_service_manager),
    ):
        self.cloud_db_repo = cloud_db_repo
        self.service_manager = service_manager

    async def __call__(
            self,
            name: str,
            project_id: str,
    ) -> CloudDbDeleteResponse:
        """Cloud DB(StatefulSet) 삭제 및 연관 리소스(PVC, SA) 정리"""

        namespace = ProjectId(project_id).namespace

        # 1. StatefulSet 조회하여 연관 PVC 목록 확인
        deployment = await self.cloud_db_repo.find_deployment(name, namespace)
        if not deployment:
            raise CloudDbNotFoundException(name=name, namespace=namespace)

        pvc_names = [v.pvc_name for v in deployment.volumes if v.pvc_name]

        # 2. Services 삭제 (headless + clusterIP)
        for svc_name in [f"{name}-headless", f"{name}-svc"]:
            try:
                await self.service_manager.delete_service(svc_name, namespace)
            except Exception:
                pass

        # 3. StatefulSet 제거
        deleted = await self.cloud_db_repo.undeploy(deployment)

        # 4. ID(ServiceAccount) 바인딩 해제
        try:
            await self.cloud_db_repo.unbind_identity(deployment.sa_name, namespace)
        except Exception:
            pass

        # 5. 스토리지 해제
        for pvc_name in pvc_names:
            try:
                await self.cloud_db_repo.deprovision_storage(pvc_name, namespace)
            except Exception:
                pass

        return CloudDbDeleteResponse(
            name=name,
            namespace=namespace,
            deleted=deleted,
        )
