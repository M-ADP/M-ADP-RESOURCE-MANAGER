from src.core.dns.provider import DnsProvider, DnsRecord
from src.core.kubernetes.service import Service, ServiceRepository
from src.core.dependencies.kubernetes import get_service_repository
from src.core.exceptions import ServiceNotFoundException
from fastapi import Depends


class ExternalDnsProvider(DnsProvider):
    """ExternalDNS를 이용하여 DNS 레코드를 관리하는 DNS 제공자"""

    def __init__(
        self,
        service_repo: ServiceRepository = Depends(get_service_repository),
    ):
        self.service_repo = service_repo

    async def create_subdomain_record(self, project_name: str, subdomain: str) -> DnsRecord:
        """
        ExternalDNS를 트리거하는 헤드리스 서비스를 생성하여 서브도메인을 등록합니다.
        TXT 레코드를 사용하여 IP 주소 없이 DNS 레코드를 선점합니다.
        """
        full_domain = f"{subdomain}.mdeveloper.platform"
        # 쿠버네티스 리소스 이름 규칙에 맞게 full_domain의 '.'을 '-'으로 변경
        service_name = f"dns-record-{subdomain}"

        # 멱등성을 위해 동일한 이름의 서비스가 있는지 확인
        existing_service = await self.service_repo.find_by_name(name=service_name, namespace=project_name)
        if existing_service:
            # 이미 존재하는 경우, 해당 DNS 정보를 반환
            # 실제로는 저장된 어노테이션 값을 읽어와야 하지만, 여기서는 예측 가능한 값을 반환합니다.
            return DnsRecord(
                name=full_domain,
                type="TXT",
                value=f"Placeholder for {full_domain}"
            )

        # Service 도메인 객체 생성 (헤드리스, no selector)
        dns_service = Service(
            name=service_name,
            namespace=project_name,
            service_type="ClusterIP",
            cluster_ip="None",  # 헤드리스 서비스로 만들기
            selector={}, # selector를 비워둠
            annotations={
                # ExternalDNS가 이 호스트네임으로 DNS 레코드를 생성하도록 함
                "external-dns.alpha.kubernetes.io/hostname": full_domain,
                # CNAME이나 A 레코드를 위한 IP가 없으므로, TXT 레코드를 생성하여 소유권을 표시
                "external-dns.alpha.kubernetes.io/txt": f"madp-dns-placeholder={full_domain}"
            }
        )

        # Service 저장 (생성)
        await self.service_repo.save(dns_service)

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
        return await self.service_repo.delete(name=service_name, namespace=project_name)

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
        target_service = await self.service_repo.find_by_name(name=target_service_name, namespace=project_name)
        if not target_service:
            raise ServiceNotFoundException()

        # 2. 호스트네임 어노테이션 추가
        full_domain = f"{subdomain}.mdeveloper.platform"
        annotated_service = target_service.with_annotations({
            "external-dns.alpha.kubernetes.io/hostname": full_domain
        })
        
        # 3. 대상 서비스 업데이트
        updated_service = await self.service_repo.save(annotated_service)

        # 4. 기존의 플레이스홀더 DNS 서비스 삭제
        placeholder_service_name = f"dns-record-{subdomain}"
        await self.service_repo.delete(name=placeholder_service_name, namespace=project_name)

        return updated_service
