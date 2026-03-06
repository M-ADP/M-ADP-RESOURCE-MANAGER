from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.kubernetes.service import Service


@dataclass(frozen=True)
class DnsRecord:
    """DNS 레코드 정보를 담는 데이터 클래스"""
    name: str
    type: str
    value: str


class DnsProvider(ABC):
    """DNS 제공자(Provider)의 추상 베이스 클래스"""

    @abstractmethod
    async def create_subdomain_record(self, project_name: str, subdomain: str) -> DnsRecord:
        """
        서브도메인에 대한 DNS 레코드를 생성합니다.

        Args:
            project_name: 프로젝트 이름 (네임스페이스로 사용)
            subdomain: 생성할 서브도메인 (예: 'my-app_deployment')

        Returns:
            생성된 DnsRecord 객체
        """
        ...
    
    @abstractmethod
    async def delete_subdomain_record(self, project_name: str, subdomain: str) -> bool:
        """
        서브도메인에 대한 DNS 레코드를 삭제합니다.

        Args:
            project_name: 프로젝트 이름 (네임스페이스)
            subdomain: 삭제할 서브도메인

        Returns:
            삭제 성공 여부
        """
        ...

    @abstractmethod
    async def update_subdomain_record(self, project_name: str, old_subdomain: str, new_subdomain: str) -> DnsRecord:
        """
        서브도메인에 대한 DNS 레코드를 수정합니다.

        Args:
            project_name: 프로젝트 이름 (네임스페이스)
            old_subdomain: 변경 전 서브도메인
            new_subdomain: 변경 후 서브도메인

        Returns:
            수정된 DnsRecord 객체
        """
        ...
    
    @abstractmethod
    async def bind_dns_to_service(self, project_name: str, subdomain: str, target_service_name: str) -> Service:
        """
        생성된 DNS 레코드를 실제 애플리케이션 서비스에 매핑(연결)합니다.

        Args:
            project_name: 프로젝트 이름 (네임스페이스)
            subdomain: 연결할 DNS의 서브도메인
            target_service_name: 연결 대상이 될 애플리케이션 서비스의 이름

        Returns:
            업데이트된 Service 객체
        """
        ...
