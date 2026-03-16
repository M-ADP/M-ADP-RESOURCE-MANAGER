"""Cloudflare API를 직접 호출하는 DNS Provider 구현체"""

from typing import Optional

import aiohttp

from src.common.config.cloudflare import CloudflareConfig
from src.core.dns import DnsProvider, DnsRecord
from src.core.logger import Logger, get_logger

_CF_API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareDnsProvider(DnsProvider):
    """Cloudflare API v4를 통해 CNAME 레코드를 관리하는 DNS Provider.

    생성되는 CNAME 레코드:
        {subdomain}.{base_domain}  →  {tunnel_id}.cfargotunnel.com
    """

    def __init__(
        self,
        config: Optional[CloudflareConfig] = None,
        logger: Optional[Logger] = None,
    ):
        self._cfg = config or CloudflareConfig()
        self.logger = logger or get_logger()

    # ── 내부 헬퍼 ────────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._cfg.api_token}",
            "Content-Type": "application/json",
        }

    def _full_domain(self, subdomain: str) -> str:
        return f"{subdomain}.{self._cfg.base_domain}"

    def _tunnel_target(self) -> str:
        return f"{self._cfg.tunnel_id}.cfargotunnel.com"

    async def _find_record_id(self, session: aiohttp.ClientSession, full_domain: str) -> Optional[str]:
        """도메인명으로 기존 CNAME 레코드 ID 조회 (없으면 None)"""
        url = f"{_CF_API_BASE}/zones/{self._cfg.zone_id}/dns_records"
        params = {"type": "CNAME", "name": full_domain}
        async with session.get(url, headers=self._headers(), params=params) as resp:
            data = await resp.json()
            records = data.get("result", [])
            return records[0]["id"] if records else None

    # ── DnsProvider 구현 ─────────────────────────────────────────────────────

    async def create_subdomain_record(self, project_name: str, subdomain: str) -> DnsRecord:
        """CNAME 레코드 생성.

        멱등성: 동일 이름 레코드가 이미 존재하면 생성 없이 반환.
        """
        full_domain = self._full_domain(subdomain)
        self.logger.info(f"Cloudflare CNAME 생성 시도: {full_domain}")

        async with aiohttp.ClientSession() as session:
            existing_id = await self._find_record_id(session, full_domain)
            if existing_id:
                self.logger.info(f"Cloudflare CNAME 이미 존재: {full_domain}")
                return DnsRecord(name=full_domain, type="CNAME", value=self._tunnel_target())

            url = f"{_CF_API_BASE}/zones/{self._cfg.zone_id}/dns_records"
            payload = {
                "type": "CNAME",
                "name": full_domain,
                "content": self._tunnel_target(),
                "ttl": self._cfg.ttl,
                "proxied": self._cfg.proxied,
            }
            async with session.post(url, headers=self._headers(), json=payload) as resp:
                data = await resp.json()
                if not data.get("success"):
                    errors = data.get("errors", [])
                    raise RuntimeError(f"Cloudflare CNAME 생성 실패: {full_domain} - {errors}")

        self.logger.info(f"Cloudflare CNAME 생성 완료: {full_domain}")
        return DnsRecord(name=full_domain, type="CNAME", value=self._tunnel_target())

    async def delete_subdomain_record(self, project_name: str, subdomain: str) -> bool:
        """CNAME 레코드 삭제.

        멱등성: 레코드가 없으면 성공으로 처리.
        """
        full_domain = self._full_domain(subdomain)
        self.logger.info(f"Cloudflare CNAME 삭제 시도: {full_domain}")

        async with aiohttp.ClientSession() as session:
            record_id = await self._find_record_id(session, full_domain)
            if not record_id:
                self.logger.info(f"Cloudflare CNAME 없음 (이미 삭제됨): {full_domain}")
                return True

            url = f"{_CF_API_BASE}/zones/{self._cfg.zone_id}/dns_records/{record_id}"
            async with session.delete(url, headers=self._headers()) as resp:
                data = await resp.json()
                if not data.get("success"):
                    errors = data.get("errors", [])
                    raise RuntimeError(f"Cloudflare CNAME 삭제 실패: {full_domain} - {errors}")

        self.logger.info(f"Cloudflare CNAME 삭제 완료: {full_domain}")
        return True

    async def update_subdomain_record(self, project_name: str, old_subdomain: str, new_subdomain: str) -> DnsRecord:
        """CNAME 레코드 수정 (기존 삭제 후 재생성)."""
        await self.delete_subdomain_record(project_name, old_subdomain)
        return await self.create_subdomain_record(project_name, new_subdomain)

