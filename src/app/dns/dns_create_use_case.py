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
from src.app.dns.exceptions import (
    DeploymentForDnsNotFoundException,
    ServiceForDnsNotFoundException,
    ServicePortNotFoundException,
)
from src.common.config.cloudflare import CloudflareConfig
from src.common.const import DefaultLabel
from src.core.dns import DnsProvider
from src.core.project import ProjectId
from src.dependencies.dns import get_dns_provider, get_tunnel_client
from src.dependencies.kubernetes import (
    get_deployment_manager,
    get_service_manager,
    get_virtualservice_manager,
)
from src.infra.dns.cloudflare_tunnel_client import CloudflareTunnelClient
from src.infra.kubernetes.managers.deployment import DeploymentManager
from src.infra.kubernetes.managers.service import ServiceManager
from src.infra.kubernetes.managers.virtualservice import IstioVirtualServiceManager
from src.core.logger import get_logger

_DNS_ID_LABEL = "madp.io/dns-id"
_DNS_SUBDOMAIN_LABEL = "madp.io/dns-subdomain"
_PROJECT_ID_LABEL = "madp.io/project-id"


class DnsCreateUseCase(BaseUseCase):
    """DNS 레코드 생성 Use Case"""

    def __init__(
        self,
        deployment_manager: DeploymentManager = Depends(get_deployment_manager),
        service_manager: ServiceManager = Depends(get_service_manager),
        virtualservice_manager: IstioVirtualServiceManager = Depends(
            get_virtualservice_manager
        ),
        dns_provider: DnsProvider = Depends(get_dns_provider),
        tunnel_client: CloudflareTunnelClient = Depends(get_tunnel_client),
    ):
        self.deployment_manager = deployment_manager
        self.service_manager = service_manager
        self.virtualservice_manager = virtualservice_manager
        self.dns_provider = dns_provider
        self.tunnel_client = tunnel_client
        self._cf = CloudflareConfig()
        self.logger = get_logger()

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
        k8s_name = deployment.metadata.labels.get(
            "app_deployment", deployment.metadata.name
        )

        # 2. 실제 Service 객체 조회하여 포트 정보 추출 (VS <-> SVC 불일치 방지)
        svc_name = f"{k8s_name}-svc"
        svc = await self.service_manager.get_service(svc_name, namespace)

        if not svc:
            raise ServiceForDnsNotFoundException(svc_name, namespace)

        if not svc.spec.ports:
            raise ServicePortNotFoundException(svc_name, namespace)

        service_port = svc.spec.ports[0].port
        self.logger.info(
            f"Service '{svc_name}' found with port {service_port}, "
            f"using this port for VirtualService destination"
        )

        full_domain = f"{subdomain}.{self._cf.base_domain}"
        service_host = f"{k8s_name}-svc.{namespace}.svc.cluster.local"

        # 3. VirtualService 생성 (istio-ingress) → 기존 Service로 FQDN 라우팅
        dns_labels = {
            _DNS_ID_LABEL: str(dns_id),
            _DNS_SUBDOMAIN_LABEL: subdomain,
            _PROJECT_ID_LABEL: payload.project_id,
            "app_deployment": k8s_name,
            **DefaultLabel.MANAGED_BY_LABEL,
        }
        vs_name = f"{k8s_name}-{subdomain}-vs"
        gateway_ref = "istio-ingress/ingressgateway"

        await self.virtualservice_manager.create_virtualservice(
            name=vs_name,
            namespace="istio-ingress",
            hosts=[full_domain],
            gateways=[gateway_ref],
            http_routes=[
                {
                    "route": [
                        {
                            "destination": {
                                "host": service_host,
                                "port": {"number": int(service_port)},
                            }
                        }
                    ],
                    "retries": {
                        "attempts": 3,
                        "perTryTimeout": "2s",
                        "retryOn": "gateway-error,connect-failure,refused-stream",
                    },
                }
            ],
            labels=dns_labels,
        )

        # 4. Tunnel Config ingress 규칙 upsert
        await self.tunnel_client.add_ingress_rule(full_domain)

        # 5. Cloudflare CNAME 생성
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
