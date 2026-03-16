from abc import ABC, abstractmethod
from dataclasses import dataclass


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
        ...

    @abstractmethod
    async def delete_subdomain_record(self, project_name: str, subdomain: str) -> bool:
        ...

    @abstractmethod
    async def update_subdomain_record(self, project_name: str, old_subdomain: str, new_subdomain: str) -> DnsRecord:
        ...
