from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectPortOpenRequest
from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_service_repository
from src.core.exceptions import ServiceAlreadyExistsException
from src.core.kubernetes.service import Service, ServicePort, ServiceRepository


class ProjectPortOpenUseCase(BaseUseCase):

    def __init__(
            self,
            service_repo: ServiceRepository = Depends(get_service_repository),
    ):
        self.service_repo = service_repo

    async def __call__(
            self,
            project_name: str,
            payload: ProjectPortOpenRequest
    ) -> Service:
        """Project 포트 개방 (Service 생성)"""
        # 1. 서비스 이름 중복 확인
        existing_service = await self.service_repo.find_by_id(id=payload.service_id, namespace=project_name)
        if existing_service:
            raise ServiceAlreadyExistsException()

        # 2. ServicePort 객체 생성
        service_port = ServicePort(
            port=payload.port,
            target_port=payload.target_port,
            protocol=payload.protocol,
            name=f"{payload.protocol.lower()}-{payload.port}" # 포트 이름 생성
        )

        # 3. Service 도메인 객체 생성
        service = Service(
            id=payload.service_id,
            name=payload.service_name,
            namespace=project_name,
            ports=[service_port],
            selector={"app": payload.target_deployment_name}, # Deployment의 레이블과 일치해야 함
            service_type=payload.service_type,
            labels={"madp.io/name": payload.service_name},
            # ExternalDNS 연동을 위한 어노테이션 추가 (예시)
            annotations={
                "external-dns.alpha.kubernetes.io/hostname": f"{payload.service_id}.{project_name}.example.com"
            } if payload.service_type == "LoadBalancer" else {}
        )

        # 4. Service 저장
        saved_service = await self.service_repo.save(service)

        return saved_service
