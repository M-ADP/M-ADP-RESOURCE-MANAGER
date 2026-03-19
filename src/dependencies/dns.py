from src.common.config.cloudflare import CloudflareConfig
from src.core.dns import DnsProvider
from src.infra.dns.cloudflare_dns_provider import CloudflareDnsProvider
from src.infra.dns.cloudflare_tunnel_client import CloudflareTunnelClient


def get_dns_provider() -> DnsProvider:
    """DnsProvider 의존성 주입 — Cloudflare 직접 호출 방식"""
    return CloudflareDnsProvider(CloudflareConfig())


def get_tunnel_client() -> CloudflareTunnelClient:
    """CloudflareTunnelClient 의존성 주입"""
    return CloudflareTunnelClient(CloudflareConfig())
