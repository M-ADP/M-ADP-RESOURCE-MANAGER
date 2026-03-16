"""DNS 레코드 생성 Use Case

흐름:
  1. x-app-deployment-id 레이블로 Deployment 조회
  2. VirtualService 생성 → subdomain.base_domain을 기존 Service로 라우팅
  3. Cloudflare CNAME 생성
"""

from fastapi import Depends

from src.api.v1.app.dns.schemas.request import DnsCreateRequest
from src.api.v1.app.dns.schemas.response import DnsCreateResponse
from src.app.base_use_case import BaseUseCase
from src.app.dns.exceptions import DeploymentForDnsNotFoundException
from src.common.config.cloudflare import CloudflareConfig
from src.common.const import DefaultLabel
from src.core.dns import DnsProvider
from src.core.project import ProjectId
from src.dependencies.dns import get_dns_provider
from src.dependencies.kubernetes import get_deployment_manager, get_virtualservice_manager
from src.infra.kubernetes.managers.deployment import DeploymentManager
from src.infra.kubernetes.managers.virtualservice import IstioVirtualServiceManager

_DNS_ID_LABEL = "madp.io/dns-id"
_DNS_SUBDOMAIN_LABEL = "madp.io/dns-subdomain"


class DnsCreateUseCase(BaseUseCase):
    """DNS 레코드 생성 Use Case"""

    def __init__(
        self,
        deployment_manager: DeploymentManager = Depends(get_deployment_manager),
        virtualservice_manager: IstioVirtualServiceManager = Depends(get_virtualservice_manager),
        dns_provider: DnsProvider = Depends(get_dns_provider),
    ):
        self.deployment_manager = deployment_manager
        self.virtualservice_manager = virtualservice_manager
        self.dns_provider = dns_provider
        self._cf = CloudflareConfig()

    async def __call__(self, payload: DnsCreateRequest) -> DnsCreateResponse:
        namespace = ProjectId(payload.project_id).namespace
        deployment_id = payload.deployment_id
        subdomain = payload.subdomain
        dns_id = payload.id

        # 1. x-app-deployment-id 레이블로 Deployment 조회
        matches = await self.deployment_manager.list_deployments(
            namespace=namespace,
            label_selector=f"x-app-deployment-id={deployment_id}",
        )
        if not matches:
            raise DeploymentForDnsNotFoundException(deployment_id, namespace)

        deployment = matches[0]
        k8s_name = deployment.metadata.labels.get("app_deployment", deployment.metadata.name)

        full_domain = f"{subdomain}.{self._cf.base_domain}"
        service_name = f"{k8s_name}-svc"
        vs_name = f"{k8s_name}-vs"
        gateway_name = f"{namespace}-gateway"

        dns_labels = {
            _DNS_ID_LABEL: str(dns_id),
            _DNS_SUBDOMAIN_LABEL: subdomain,
            "app_deployment": k8s_name,
            **DefaultLabel.MANAGED_BY_LABEL,
        }

        # 2. VirtualService 생성 → 기존 Service({k8s_name}-svc)로 라우팅
        await self.virtualservice_manager.create_virtualservice(
            name=vs_name,
            namespace=namespace,
            hosts=[full_domain],
            gateways=[gateway_name],
            http_routes=[{
                "route": [{
                    "destination": {
                        "host": service_name,
                    }
                }]
            }],
            labels=dns_labels,
        )

        # 3. Cloudflare CNAME 생성
        await self.dns_provider.create_subdomain_record(
            project_name=namespace,
            subdomain=subdomain,
        )

        return DnsCreateResponse(
            id=dns_id,
            project_id=payload.project_id,
            deployment_id=k8s_name,
            subdomain=subdomain,
            hostname=full_domain,
        )
