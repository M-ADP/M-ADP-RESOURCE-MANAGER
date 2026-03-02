from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectPortOpenRequest
from src.app.base_use_case import BaseUseCase
from src.core.project import ProjectRepository
from src.core.kubernetes.service import ServiceAlreadyExistsException, Service, ServicePort
from src.dependencies.kubernetes import get_project_repository


class ProjectPortOpenUseCase(BaseUseCase):

    def __init__(
            self,
            project_repo: ProjectRepository = Depends(get_project_repository),
    ):
        self.project_repo = project_repo

    async def __call__(
            self,
            project_name: str,
            payload: ProjectPortOpenRequest
    ) -> Service:
        """Project 포트 개방 (Service 생성)"""

        # 1. 서비스 이름 중복 확인
        existing_service = await self.project_repo.find_service(id=payload.service_id, namespace=project_name)
        if existing_service:
            raise ServiceAlreadyExistsException()

        # 2. Enum에서 값 추출
        protocol_value = payload.protocol.value if hasattr(payload.protocol, 'value') else payload.protocol
        service_type_value = payload.service_type.value if hasattr(payload.service_type, 'value') else payload.service_type

        # 3. Service 도메인 객체 생성
        service_port = ServicePort(
            port=payload.port,
            target_port=payload.target_port,
            protocol=protocol_value,
            name=f"{protocol_value.lower()}-{payload.port}",
        )

        service = Service(
            id=payload.service_id,
            name=payload.service_name,
            namespace=project_name,
            ports=[service_port],
            selector={"app_deployment": payload.target_deployment_name},
            service_type=service_type_value,
            labels={"madp.io/name": payload.service_name},
            annotations={
                "external-dns.alpha.kubernetes.io/hostname": f"{payload.service_id}.{project_name}.mdeveloper.platform"
            } if service_type_value == "LoadBalancer" else {},
        )

        # 4. Service 저장
        return await self.project_repo.save_service(service)
