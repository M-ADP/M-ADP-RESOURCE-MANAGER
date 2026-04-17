import aiohttp
from typing import Any, Dict, List, Optional
from src.common.config.jenkins import JenkinsConfig
from src.core.logger import Logger


class JenkinsClient:
    """Jenkins API 클라이언트"""

    def __init__(self, config: JenkinsConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self.auth = None
        if config.user and config.token:
            self.auth = aiohttp.BasicAuth(config.user, config.token)

    async def get_builds(self, job_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """빌드 목록 조회"""
        target_job = job_name or self.config.job_name
        url = f"{self.config.url}/job/{target_job}/api/json"
        params = {"tree": "builds[number,result,timestamp,duration,actions[parameters[name,value]]]"}

        async with aiohttp.ClientSession(auth=self.auth) as session:
            try:
                async with session.get(url, params=params, timeout=self.config.timeout) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to fetch Jenkins builds: {response.status}")
                        return []
                    data = await response.json()
                    return data.get("builds", [])
            except Exception as e:
                self.logger.error(f"Error fetching Jenkins builds: {str(e)}")
                return []

    async def get_console_text(self, build_number: int, job_name: Optional[str] = None) -> str:
        """빌드 콘솔 로그 조회"""
        target_job = job_name or self.config.job_name
        url = f"{self.config.url}/job/{target_job}/{build_number}/consoleText"

        async with aiohttp.ClientSession(auth=self.auth) as session:
            try:
                async with session.get(url, timeout=self.config.timeout) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to fetch Jenkins console text for build {build_number}: {response.status}")
                        return f"Error: Failed to fetch logs (Status {response.status})"
                    return await response.text()
            except Exception as e:
                self.logger.error(f"Error fetching Jenkins console text: {str(e)}")
                return f"Error: {str(e)}"
