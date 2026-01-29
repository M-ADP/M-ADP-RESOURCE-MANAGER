from src.core.dns.provider import DnsProvider
from src.infra.dns.external_dns_provider import ExternalDnsProvider


def get_dns_provider() -> DnsProvider:
    """
    DnsProvider 의존성 주입

    현재는 ExternalDnsProvider를 반환합니다.
    향후 다른 DNS 제공자가 추가되면, 설정에 따라 다른 Provider를 반환하도록 수정할 수 있습니다.
    """
    return ExternalDnsProvider()
