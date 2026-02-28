from kubernetes_asyncio.client import V1Service

from src.core.dns import DnsProvider, DnsRecord
from src.core.kubernetes.service import Service, ServicePort, ServiceNotFoundException
from src.dependencies.kubernetes import get_service_manager
from src.infra.kubernetes.managers.service import ServiceManager
from fastapi import Depends


class ExternalDnsProvider(DnsProvider):
    """ExternalDNS를 이용하여 DNS 레코드를 관리하는 DNS 제공자"""

    def __init__(
        self,
        service_manager: ServiceManager = Depends(get_service_manager),
    ):
        self.service_manager = service_manager

    def _to_domain(self, v1_svc: V1Service) -> Service:
        """V1Service를 도메인 객체로 변환"""
        ports = []
        if v1_svc.spec and v1_svc.spec.ports:
            for p in v1_svc.spec.ports:
                target_port = p.target_port if isinstance(p.target_port, int) else int(p.target_port)
                ports.append(ServicePort(
                    port=p.port,
                    target_port=target_port,
                    protocol=p.protocol or "TCP",
                    name=p.name,
                    node_port=p.node_port,
                ))
        labels = v1_svc.metadata.labels or {}
        return Service(
            id=v1_svc.metadata.name,
            name=labels.get("madp.io/name", ""),
            namespace=v1_svc.metadata.namespace,
            ports=ports,
            selector=v1_svc.spec.selector if v1_svc.spec else {},
            service_type=v1_svc.spec.type if v1_svc.spec else "ClusterIP",
            labels=labels,
            annotations=v1_svc.metadata.annotations or {},
            cluster_ip=v1_svc.spec.cluster_ip if v1_svc.spec else None,
            external_ips=v1_svc.spec.external_ips if v1_svc.spec and v1_svc.spec.external_ips else [],
        )

    async def create_subdomain_record(self, project_name: str, subdomain: str) -> DnsRecord:
        """
        ExternalDNS를 트리거하는 헤드리스 서비스를 생성하여 서브도메인을 등록합니다.
        TXT 레코드를 사용하여 IP 주소 없이 DNS 레코드를 선점합니다.
        """
        full_domain = f"{subdomain}.mdeveloper.platform"
        # 쿠버네티스 리소스 이름 규칙에 맞게 full_domain의 '.'을 '-'으로 변경
        service_name = f"dns-record-{subdomain}"

        # 멱등성을 위해 동일한 이름의 서비스가 있는지 확인
        existing_service = await self.service_manager.get_service(service_name, project_name)
        if existing_service:
            # 이미 존재하는 경우, 해당 DNS 정보를 반환
            return DnsRecord(
                name=full_domain,
                type="TXT",
                value=f"Placeholder for {full_domain}"
            )

        await self.service_manager.create_service(
            name=service_name,
            namespace=project_name,
            selector={},
            ports=[],
            service_type="ClusterIP",
            cluster_ip="None",
            annotations={
                "external-dns.alpha.kubernetes.io/hostname": full_domain,
                "external-dns.alpha.kubernetes.io/txt": f"madp-dns-placeholder={full_domain}"
            },
        )

        return DnsRecord(
            name=full_domain,
            type="TXT",
            value=f"madp-dns-placeholder={full_domain}"
        )

    async def delete_subdomain_record(self, project_name: str, subdomain: str) -> bool:
        """
        서브도메인에 해당하는 헤드리스 서비스를 삭제하여 DNS 레코드를 제거합니다.
        """
        service_name = f"dns-record-{subdomain}"
        return await self.service_manager.delete_service(service_name, project_name)

    async def update_subdomain_record(self, project_name: str, old_subdomain: str, new_subdomain: str) -> DnsRecord:
        """
        기존 DNS 레코드를 삭제하고 새로운 DNS 레코드를 생성하여 서브도메인을 수정합니다.
        """
        # 1. 기존 레코드(서비스) 삭제
        await self.delete_subdomain_record(project_name, old_subdomain)

        # 2. 새로운 레코드(서비스) 생성
        new_record = await self.create_subdomain_record(project_name, new_subdomain)

        return new_record

    async def bind_dns_to_service(self, project_name: str, subdomain: str, target_service_name: str) -> Service:
        """
        생성된 DNS 레코드를 실제 애플리케이션 서비스에 매핑(연결)합니다.
        """
        # 1. 대상 애플리케이션 서비스 조회
        target_v1_service = await self.service_manager.get_service(target_service_name, project_name)
        if not target_v1_service:
            raise ServiceNotFoundException()

        # 2. 호스트네임 어노테이션 추가
        full_domain = f"{subdomain}.mdeveloper.platform"
        updated_v1_service = await self.service_manager.update_annotations(
            name=target_service_name,
            namespace=project_name,
            annotations={"external-dns.alpha.kubernetes.io/hostname": full_domain},
            merge=True,
        )

        # 3. 기존의 플레이스홀더 DNS 서비스 삭제
        placeholder_service_name = f"dns-record-{subdomain}"
        await self.service_manager.delete_service(placeholder_service_name, project_name)

        return self._to_domain(updated_v1_service)
