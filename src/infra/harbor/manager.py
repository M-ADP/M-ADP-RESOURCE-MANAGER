"""Harbor API Client"""

import aiohttp
from typing import Optional, Dict, Any

from src.common.config.harbor import HarborConfig
from src.core.logger import Logger, get_logger


class HarborManager:
    """Harbor API Manager"""

    def __init__(
        self,
        harbor_config: Optional[HarborConfig] = None,
        logger: Optional[Logger] = None,
    ):
        self._config = harbor_config or HarborConfig()
        self._logger = logger or get_logger()

    @property
    def base_url(self) -> str:
        return self._config.url

    @property
    def username(self) -> str:
        return self._config.username

    @property
    def password(self) -> str:
        return self._config.password

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Harbor API 요청"""
        url = f"http://{self.base_url}/api/v2.0{path}"
        auth = aiohttp.BasicAuth(self.username, self.password)

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, auth=auth, **kwargs) as resp:
                if resp.status == 204:
                    return {}
                if resp.status >= 400:
                    text = await resp.text()
                    raise Exception(f"Harbor API error: {resp.status} - {text}")
                return await resp.json()

    async def create_project(self, project_name: str) -> Dict[str, Any]:
        """Harbor 프로젝트 생성 (멱등성)"""
        self.logger.info(f"Harbor 프로젝트 생성: {project_name}")

        try:
            return await self._request(
                "POST",
                "/projects",
                json={
                    "project_name": project_name,
                    "public": False,
                },
            )
        except Exception as e:
            if "already exists" in str(e).lower() or e.__class__.__name__ == "KeyError":
                self.logger.info(f"Harbor 프로젝트 이미 존재: {project_name}")
                return await self.get_project(project_name)
            raise

    async def get_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Harbor 프로젝트 조회"""
        try:
            return await self._request("GET", f"/projects/{project_name}")
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise

    async def delete_project(self, project_name: str) -> bool:
        """Harbor 프로젝트 삭제"""
        await self._request("DELETE", f"/projects/{project_name}")
        return True

    async def project_exists(self, project_name: str) -> bool:
        """프로젝트 존재 여부 확인"""
        project = await self.get_project(project_name)
        return project is not None

    @property
    def logger(self) -> Logger:
        return self._logger
