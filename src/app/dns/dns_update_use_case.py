"""DNS 레코드 수정 Use Case

흐름:
  1. dns_id 레이블로 기존 VirtualService 조회
  2. 기존 Cloudflare CNAME 삭제
  3. VirtualService hosts 업데이트 (patch)
  4. Service 레이블 업데이트 (subdomain 레이블만 변경)
  5. 새 Cloudflare CNAME 생성
"""

from fastapi import Depends

from src.api.v1.app.dns.schemas.request import DnsUpdateRequest
from src.api.v1.app.dns.schemas.response import DnsUpdateResponse
from src.app.base_use_case import BaseUseCase
from src.app.dns.exceptions import DnsRecordNotFoundException
from src.common.config.cloudflare import CloudflareConfig
from src.common.config.istio import IstioConfig
from src.core.dns import DnsProvider
from src.core.project import ProjectId
from src.dependencies.dns import get_dns_provider, get_istio_config, get_tunnel_client
from src.dependencies.kubernetes import get_virtualservice_manager
from src.infra.dns.cloudflare_tunnel_client import CloudflareTunnelClient
from src.infra.kubernetes.managers.virtualservice import IstioVirtualServiceManager

_DNS_ID_LABEL = "madp.io/dns-id"
_DNS_SUBDOMAIN_LABEL = "madp.io/dns-subdomain"


class DnsUpdateUseCase(BaseUseCase):
    """DNS 서브도메인 수정 Use Case"""

    def __init__(
        self,
        virtualservice_manager: IstioVirtualServiceManager = Depends(get_virtualservice_manager),
        dns_provider: DnsProvider = Depends(get_dns_provider),
        tunnel_client: CloudflareTunnelClient = Depends(get_tunnel_client),
        istio_config: IstioConfig = Depends(get_istio_config),
    ):
        self.virtualservice_manager = virtualservice_manager
        self.dns_provider = dns_provider
        self.tunnel_client = tunnel_client
        self._cf = CloudflareConfig()
        self._istio = istio_config

    async def __call__(self, dns_id: str, payload: DnsUpdateRequest) -> DnsUpdateResponse:
        namespace = ProjectId(payload.project_id).namespace

        # 1. dns_id 레이블로 기존 VirtualService 조회
        vs = await self.virtualservice_manager.find_by_label(f"{_DNS_ID_LABEL}={dns_id}")
        if not vs:
            raise DnsRecordNotFoundException(dns_id)

        vs_name = vs["metadata"]["name"]
        old_subdomain = vs["metadata"]["labels"].get(_DNS_SUBDOMAIN_LABEL, "")
        new_subdomain = payload.subdomain
        new_full_domain = f"{new_subdomain}.{self._cf.base_domain}"

        old_full_domain = f"{old_subdomain}.{self._cf.base_domain}"

        # 2. 기존 Cloudflare CNAME 삭제
        await self.dns_provider.delete_subdomain_record(
            project_name=namespace,
            subdomain=old_subdomain,
        )

        # 3. Tunnel Config ingress 규칙 변경 (단일 GET/PUT)
        await self.tunnel_client.update_ingress_rule(old_full_domain, new_full_domain)

        # 4. VirtualService hosts + 레이블 patch
        await self.virtualservice_manager.patch_virtualservice(
            name=vs_name,
            namespace=self._istio.gateway_namespace,
            hosts=[new_full_domain],
            label_patch={_DNS_SUBDOMAIN_LABEL: new_subdomain},
        )

        # 5. 새 Cloudflare CNAME 생성
        await self.dns_provider.create_subdomain_record(
            project_name=namespace,
            subdomain=new_subdomain,
        )

        return DnsUpdateResponse(
            id=dns_id,
            project_id=payload.project_id,
            deployment_id=payload.deployment_id,
            subdomain=new_subdomain,
            hostname=new_full_domain,
        )
