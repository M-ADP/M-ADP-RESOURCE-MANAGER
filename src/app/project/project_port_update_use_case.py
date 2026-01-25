from fastapi import Depends

from src.core.exceptions import ServiceNotFoundException, PortNotFoundException
from src.api.v1.project.schmas.request import ProjectPortUpdateRequest
from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_service_repository
from src.core.kubernetes.service import Service, ServiceRepository

class ProjectPortUpdateUseCase(BaseUseCase):

    def __init__(
            self,
            service_repo: ServiceRepository = Depends(get_service_repository),
    ):
        self.service_repo = service_repo

    async def __call__(
            self,
            project_name: str,
            port_number: int, # Path parameter로 받은 포트 번호 (업데이트 대상 포트)
            payload: ProjectPortUpdateRequest
    ) -> Service:
        """Project 포트 수정 (Service 업데이트)"""
        # 1. 기존 Service 조회
        # payload.service_id을 사용하여 서비스 조회
        existing_service = await self.service_repo.find_by_id(id=payload.service_id, namespace=project_name)
        if not existing_service:
            raise ServiceNotFoundException()

        updated_service = existing_service

        # 2. Selector 업데이트
        if payload.target_deployment_name:
            updated_service = updated_service.with_selector({"app": payload.target_deployment_name})
        
        if payload.service_name:
            updated_service = updated_service.with_labels({"madp.io/name": payload.service_name})

        # 3. Service Type 업데이트
        if payload.service_type:
            updated_service = updated_service.with_service_type(payload.service_type)
            # Service Type이 LoadBalancer로 변경되면 ExternalDNS 어노테이션 추가
            if payload.service_type == "LoadBalancer":
                 updated_service = updated_service.with_annotations({
                    "external-dns.alpha.kubernetes.io/hostname": f"{payload.service_id}.{project_name}.example.com"
                })
            else: # 그 외의 타입일 경우 ExternalDNS 어노테이션 제거
                # TODO: 기존 어노테이션에서 external-dns 어노테이션만 제거하는 로직 필요
                # 현재는 기존 어노테이션이 유지되므로, 명시적으로 제거하는 로직이 필요
                pass # 일단은 그냥 둠

        # 4. Port 정보 업데이트 (target_port, protocol)
        if payload.target_port or payload.protocol:
            updated_service = updated_service.update_port_by_number(
                port_number=port_number, # Path parameter의 port_id 사용
                new_target_port=payload.target_port,
                new_protocol=payload.protocol
            )
            # 포트 번호에 해당하는 포트가 Service에 없는 경우 예외 처리
            if updated_service == existing_service and (payload.target_port or payload.protocol):
                 raise PortNotFoundException()


        # 5. Service 저장 (업데이트)
        saved_service = await self.service_repo.save(updated_service)

        return saved_service
