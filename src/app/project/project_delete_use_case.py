from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.project.schmas.response import ProjectDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.app.project.exceptions import ProjectNotFoundException
from src.common.config.cloudflare import CloudflareConfig
from src.core.dns import DnsProvider
from src.core.project import ProjectRepository
from src.dependencies.dns import get_dns_provider, get_tunnel_client
from src.dependencies.kubernetes import (
    get_project_repository,
    get_virtualservice_manager,
)
from src.infra.dns.cloudflare_tunnel_client import CloudflareTunnelClient
from src.infra.kubernetes.managers.virtualservice import IstioVirtualServiceManager

_PROJECT_ID_LABEL = "madp.io/project-id"
_DNS_SUBDOMAIN_LABEL = "madp.io/dns-subdomain"


class ProjectDeleteUseCase(BaseUseCase):
    def __init__(
        self,
        project_repo: ProjectRepository = Depends(get_project_repository),
        virtualservice_manager: IstioVirtualServiceManager = Depends(
            get_virtualservice_manager
        ),
        dns_provider: DnsProvider = Depends(get_dns_provider),
        tunnel_client: CloudflareTunnelClient = Depends(get_tunnel_client),
    ):
        self.project_repo = project_repo
        self.virtualservice_manager = virtualservice_manager
        self.dns_provider = dns_provider
        self.tunnel_client = tunnel_client
        self._cf = CloudflareConfig()

    async def __call__(self, id: str, user_id: str) -> ProjectDeleteResponse:
        """Project 삭제 (ResourceQuota + Namespace + Harbor + DNS)"""
        project_id = id
        namespace_id = ProjectId(project_id).namespace

        # 1. Project 존재 여부 확인
        if not await self.project_repo.exists_namespace(namespace_id):
            raise ProjectNotFoundException()

        # 2. 프로젝트 연관 DNS 레코드 정리
        dns_deleted_count = 0
        try:
            # istio-system 네임스페이스에서 해당 프로젝트 레이블이 달린 모든 VirtualService 조회
            vss = await self.virtualservice_manager.list_by_label(
                label_selector=f"{_PROJECT_ID_LABEL}={project_id}"
            )
            for vs in vss:
                meta = vs["metadata"]
                vs_name = meta["name"]
                vs_ns = meta["namespace"]
                subdomain = meta["labels"].get(_DNS_SUBDOMAIN_LABEL)

                if subdomain:
                    # Cloudflare CNAME 삭제
                    await self.dns_provider.delete_subdomain_record(
                        project_name=namespace_id,
                        subdomain=subdomain,
                    )

                    # Tunnel Config ingress 규칙 삭제
                    full_domain = f"{subdomain}.{self._cf.base_domain}"
                    await self.tunnel_client.remove_ingress_rule(full_domain)

                # VirtualService 삭제
                await self.virtualservice_manager.delete_virtualservice(vs_name, vs_ns)
                dns_deleted_count += 1
        except Exception:
            # DNS 삭제 중 오류가 발생해도 프로젝트 삭제는 계속 진행 (Best effort)
            pass

        quota_id = f"{namespace_id}-quota"

        # 3. ResourceQuota 삭제 (존재하는 경우)
        resource_quota_deleted = False
        if await self.project_repo.exists_resource_quota(quota_id, namespace_id):
            await self.project_repo.delete_resource_quota(quota_id, namespace_id)
            resource_quota_deleted = True

        # 4. Namespace 삭제 (내부 모든 자원 자동 삭제)
        await self.project_repo.delete_namespace(namespace_id)

        # 5. Harbor 프로젝트 삭제
        harbor_deleted = False
        try:
            await self.project_repo.delete_project_from_harbor(project_id)
            harbor_deleted = True
        except Exception:
            pass

        return ProjectDeleteResponse(
            namespace_id=namespace_id,
            resource_quota_deleted=resource_quota_deleted,
            harbor_deleted=harbor_deleted,
            dns_deleted_count=dns_deleted_count,  # 필요 시 응답 스키마에 추가
        )

