"""Cloudflare Zero Trust Tunnel Config ingress 규칙 관리"""

from typing import Optional

import aiohttp

from src.common.config.cloudflare import CloudflareConfig
from src.core.logger import Logger, get_logger

_CF_API_BASE = "https://api.cloudflare.com/client/v4"
_CATCH_ALL = {"service": "http_status:404"}


class CloudflareTunnelClient:
    """Cloudflare Tunnel Config API를 통해 ingress 규칙을 관리.

    모든 subdomain은 Istio IngressGateway(gateway_url)로 라우팅.
    add_ingress_rule / remove_ingress_rule 은 upsert/idempotent 처리.
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

    def _config_url(self) -> str:
        return (
            f"{_CF_API_BASE}/accounts/{self._cfg.account_id}"
            f"/cfdtunnel/{self._cfg.tunnel_id}/configurations"
        )

    async def _get_ingress(self, session: aiohttp.ClientSession) -> list:
        """현재 터널 ingress 규칙 목록 반환. 없으면 catch-all만 포함한 빈 목록."""
        async with session.get(self._config_url(), headers=self._headers()) as resp:
            data = await resp.json()
            if not data.get("success"):
                raise RuntimeError(f"Tunnel Config 조회 실패: {data.get('errors')}")
            ingress = data.get("result", {}).get("config", {}).get("ingress", [])
            return ingress if ingress else [_CATCH_ALL]

    async def _put_ingress(self, session: aiohttp.ClientSession, ingress: list) -> None:
        """ingress 규칙 전체 교체. catch-all이 마지막에 없으면 자동 추가."""
        if not ingress or ingress[-1] != _CATCH_ALL:
            ingress = [r for r in ingress if r != _CATCH_ALL] + [_CATCH_ALL]

        payload = {"config": {"ingress": ingress}}
        async with session.put(self._config_url(), headers=self._headers(), json=payload) as resp:
            data = await resp.json()
            if not data.get("success"):
                raise RuntimeError(f"Tunnel Config 업데이트 실패: {data.get('errors')}")

    # ── Public API ────────────────────────────────────────────────────────────

    async def add_ingress_rule(self, hostname: str) -> None:
        """hostname → gateway_url ingress 규칙 upsert.

        이미 존재하면 교체, 없으면 catch-all 직전에 삽입.
        """
        self.logger.info(f"Tunnel ingress 규칙 upsert: {hostname}")
        new_rule = {"hostname": hostname, "service": self._cfg.gateway_url}

        async with aiohttp.ClientSession() as session:
            ingress = await self._get_ingress(session)

            for i, rule in enumerate(ingress):
                if rule.get("hostname") == hostname:
                    ingress[i] = new_rule
                    self.logger.info(f"Tunnel ingress 규칙 교체 완료: {hostname}")
                    await self._put_ingress(session, ingress)
                    return

            ingress.insert(-1, new_rule)
            self.logger.info(f"Tunnel ingress 규칙 추가 완료: {hostname}")
            await self._put_ingress(session, ingress)

    async def remove_ingress_rule(self, hostname: str) -> None:
        """hostname ingress 규칙 삭제. 없으면 성공으로 처리 (idempotent)."""
        self.logger.info(f"Tunnel ingress 규칙 삭제 시도: {hostname}")

        async with aiohttp.ClientSession() as session:
            ingress = await self._get_ingress(session)
            filtered = [r for r in ingress if r.get("hostname") != hostname]

            if len(filtered) == len(ingress):
                self.logger.info(f"Tunnel ingress 규칙 없음 (이미 삭제됨): {hostname}")
                return

            self.logger.info(f"Tunnel ingress 규칙 삭제 완료: {hostname}")
            await self._put_ingress(session, filtered)

    async def update_ingress_rule(self, old_hostname: str, new_hostname: str) -> None:
        """hostname 변경. 단일 GET/PUT으로 처리."""
        self.logger.info(f"Tunnel ingress 규칙 변경: {old_hostname} → {new_hostname}")
        new_rule = {"hostname": new_hostname, "service": self._cfg.gateway_url}

        async with aiohttp.ClientSession() as session:
            ingress = await self._get_ingress(session)
            updated = False

            for i, rule in enumerate(ingress):
                if rule.get("hostname") == old_hostname:
                    ingress[i] = new_rule
                    updated = True
                    break

            if not updated:
                ingress.insert(-1, new_rule)

            self.logger.info(f"Tunnel ingress 규칙 변경 완료: {new_hostname}")
            await self._put_ingress(session, ingress)
