"""App Deployment 삭제 Use Case"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.response import AppDeleteResponse
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.app.base_use_case import BaseUseCase
from src.common.config.cloudflare import CloudflareConfig
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.core.dns import DnsProvider
from src.dependencies.dns import get_dns_provider, get_tunnel_client
from src.dependencies.kubernetes import (
    get_app_deployment_repository,
    get_service_manager,
    get_virtualservice_manager,
)
from src.infra.dns.cloudflare_tunnel_client import CloudflareTunnelClient
from src.infra.kubernetes.managers.service import ServiceManager
from src.infra.kubernetes.managers.virtualservice import IstioVirtualServiceManager

_DNS_ID_LABEL = "madp.io/dns-id"
_DNS_SUBDOMAIN_LABEL = "madp.io/dns-subdomain"


class AppDeploymentDeleteUseCase(BaseUseCase):
    """App Deployment 삭제 Use Case"""

    def __init__(
            self,
            app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
            service_manager: ServiceManager = Depends(get_service_manager),
            virtualservice_manager: IstioVirtualServiceManager = Depends(get_virtualservice_manager),
            dns_provider: DnsProvider = Depends(get_dns_provider),
            tunnel_client: CloudflareTunnelClient = Depends(get_tunnel_client),
    ):
        self.app_deployment_repo = app_deployment_repo
        self.service_manager = service_manager
        self.virtualservice_manager = virtualservice_manager
        self.dns_provider = dns_provider
        self.tunnel_client = tunnel_client
        self._cf = CloudflareConfig()

    async def __call__(
            self,
            app_name: str,
            project_id: str,
    ) -> AppDeleteResponse:
        """App(Deployment) 삭제 및 연관 리소스(DNS, PVC, SA) 정리"""

        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        # 1. Deployment 조회하여 연관 PVC 목록 확인
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        pvc_names = [v.pvc_name for v in deployment.volumes if v.pvc_name]

        # 2. DNS(VirtualService) 존재 시 삭제
        await self._delete_dns_if_exists(app_name)

        # 3. Service 삭제 (존재하지 않아도 무시)
        try:
            await self.service_manager.delete_service(f"{app_name}-svc", namespace)
        except Exception:
            pass

        # 4. Deployment 제거
        deleted = await self.app_deployment_repo.undeploy(deployment)

        # 5. ID(ServiceAccount) 바인딩 해제 (deployment.sa_name 자동 활용)
        try:
            await self.app_deployment_repo.unbind_identity(deployment.sa_name, namespace)
        except Exception:
            pass

        # 6. 스토리지 해제
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

    async def _delete_dns_if_exists(self, app_name: str) -> None:
        """app_name 레이블로 연결된 VirtualService(DNS) 전체 삭제."""
        try:
            vs_list = await self.virtualservice_manager.list_by_label(f"app_deployment={app_name}")
        except Exception:
            return

        for vs in vs_list:
            try:
                meta = vs["metadata"]
                vs_name = meta["name"]
                vs_namespace = meta["namespace"]
                subdomain = meta["labels"].get(_DNS_SUBDOMAIN_LABEL, "")

                await self.dns_provider.delete_subdomain_record(
                    project_name=vs_namespace,
                    subdomain=subdomain,
                )

                full_domain = f"{subdomain}.{self._cf.base_domain}"
                await self.tunnel_client.remove_ingress_rule(full_domain)

                await self.virtualservice_manager.delete_virtualservice(vs_name, vs_namespace)
            except Exception:
                pass
