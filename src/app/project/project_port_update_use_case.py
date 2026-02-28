from fastapi import Depends

from src.core.kubernetes.service import ServiceNotFoundException, PortNotFoundException
from src.api.v1.project.schmas.request import ProjectPortUpdateRequest
from src.app.base_use_case import BaseUseCase
from src.core.project import ProjectRepository
from src.core.kubernetes.service import Service
from src.dependencies.kubernetes import get_project_repository


class ProjectPortUpdateUseCase(BaseUseCase):

    def __init__(
            self,
            project_repo: ProjectRepository = Depends(get_project_repository),
    ):
        self.project_repo = project_repo

    async def __call__(
            self,
            project_name: str,
            payload: ProjectPortUpdateRequest
    ) -> Service:
        """Project 포트 수정 (Service 업데이트)"""

        # 1. 기존 Service 조회
        existing_service = await self.project_repo.find_service(id=payload.service_id, namespace=project_name)
        if not existing_service:
            raise ServiceNotFoundException()

        updated_service = existing_service

        # 2. Selector 업데이트
        if payload.target_deployment_name:
            updated_service = updated_service.with_selector({"app_deployment": payload.target_deployment_name})

        if payload.service_name:
            updated_service = updated_service.with_labels({"madp.io/name": payload.service_name})

        # 3. Service Type 업데이트
        if payload.service_type:
            updated_service = updated_service.with_service_type(payload.service_type)
            if payload.service_type == "LoadBalancer":
                updated_service = updated_service.with_annotations({
                    "external-dns.alpha.kubernetes.io/hostname": f"{payload.service_id}.{project_name}.example.com"
                })

        # 4. Port 정보 업데이트
        if payload.target_port or payload.protocol:
            if not existing_service.ports:
                raise PortNotFoundException()

            first_port_number = existing_service.ports[0].port
            updated_service = updated_service.update_port_by_number(
                port_number=first_port_number,
                new_target_port=payload.target_port,
                new_protocol=payload.protocol,
            )

        # 5. Service 저장
        return await self.project_repo.save_service(updated_service)
