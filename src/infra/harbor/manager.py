"""Harbor API Client"""

import gzip
import io
import tarfile
import aiohttp
from typing import Optional, Dict, Any, List, Tuple
from fastapi import Depends

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
                if resp.status in (204, 201):
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

    async def get_artifact_vulnerabilities(
        self, project_name: str, repository_name: str, reference: str
    ) -> Dict[str, Any]:
        """아티팩트(이미지) 취약점 스캔 결과 조회"""
        # repository_name에 /가 포함된 경우 (예: "my-app/backend") URL 인코딩 필요할 수 있음
        repo_path = repository_name.replace("/", "%2F")
        path = f"/projects/{project_name}/repositories/{repo_path}/artifacts/{reference}/additions/vulnerabilities"
        try:
            return await self._request("GET", path)
        except Exception as e:
            self.logger.warning(f"Harbor 취약점 조회 실패: {project_name}/{repository_name}:{reference} - {str(e)}")
            return {}

    async def project_exists(self, project_name: str) -> bool:
        """프로젝트 존재 여부 확인"""
        project = await self.get_project(project_name)
        return project is not None

    # ── Image GID 탐지 ────────────────────────────────────────────────────────

    async def get_image_fs_group(self, full_image: str) -> Optional[int]:
        """이미지의 실행 유저 GID를 탐지하여 반환.

        Docker Registry v2 API로 이미지 config를 가져와 User 필드를 파싱한다.
        숫자 형식(UID:GID)이면 GID를 직접 추출하고,
        이름 형식(username)이면 이미지 레이어에서 /etc/passwd를 스캔해 GID를 해석한다.
        탐지 불가 시 None 반환 (fsGroup 미설정).
        """
        try:
            registry, repo, reference = self._parse_image_ref(full_image)
            manifest = await self._get_manifest(registry, repo, reference)
            config_digest = manifest["config"]["digest"]
            config = await self._get_blob_json(registry, repo, config_digest)

            user_str = (config.get("config") or {}).get("User") or ""
            if not user_str:
                return None

            gid = self._parse_numeric_gid(user_str)
            if gid is not None:
                return gid

            # username 형식 → 레이어 스캔으로 /etc/passwd에서 GID 해석
            username = user_str.split(":")[0]
            layers: List[Dict] = manifest.get("layers", [])
            return await self._resolve_gid_from_layers(registry, repo, layers, username)

        except Exception as e:
            self._logger.warning(f"이미지 GID 탐지 실패 ({full_image}): {e}")
            return None

    def _parse_image_ref(self, full_image: str) -> Tuple[str, str, str]:
        """full_image → (registry, repository, reference) 분해.

        예: harbor.local/proj/app:tag → ('harbor.local', 'proj/app', 'tag')
        """
        slash_idx = full_image.find("/")
        if slash_idx == -1:
            return self._config.url, full_image, "latest"
        registry = full_image[:slash_idx]
        rest = full_image[slash_idx + 1:]
        if ":" in rest:
            repo, reference = rest.rsplit(":", 1)
        else:
            repo, reference = rest, "latest"
        return registry, repo, reference

    async def _get_manifest(self, registry: str, repo: str, reference: str) -> Dict:
        """Docker Registry v2 이미지 manifest 조회."""
        url = f"http://{registry}/v2/{repo}/manifests/{reference}"
        headers = {
            "Accept": (
                "application/vnd.docker.distribution.manifest.v2+json, "
                "application/vnd.oci.image.manifest.v1+json"
            )
        }
        auth = aiohttp.BasicAuth(self._config.username, self._config.password)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)

    async def _get_blob_json(self, registry: str, repo: str, digest: str) -> Dict:
        """Registry blob(config 등) JSON 조회."""
        url = f"http://{registry}/v2/{repo}/blobs/{digest}"
        auth = aiohttp.BasicAuth(self._config.username, self._config.password)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)

    def _parse_numeric_gid(self, user_str: str) -> Optional[int]:
        """User 필드에서 숫자 GID 추출.

        'UID:GID' → GID, 'UID' → UID, 이름 형식 → None.
        """
        parts = user_str.split(":")
        try:
            if len(parts) >= 2:
                return int(parts[1])
            return int(parts[0])
        except ValueError:
            return None

    async def _resolve_gid_from_layers(
        self,
        registry: str,
        repo: str,
        layers: List[Dict],
        username: str,
    ) -> Optional[int]:
        """이미지 레이어를 최신 순으로 스캔해 /etc/passwd에서 username의 GID 반환."""
        _MAX_LAYER_BYTES = 150 * 1024 * 1024  # 150 MB 초과 레이어 스킵
        for layer in reversed(layers):
            if int(layer.get("size", 0)) > _MAX_LAYER_BYTES:
                continue
            gid = await self._scan_layer_for_gid(registry, repo, layer["digest"], username)
            if gid is not None:
                return gid
        return None

    async def _scan_layer_for_gid(
        self,
        registry: str,
        repo: str,
        digest: str,
        username: str,
    ) -> Optional[int]:
        """단일 레이어(gzip tar) 를 다운로드하여 /etc/passwd에서 GID를 파싱."""
        url = f"http://{registry}/v2/{repo}/blobs/{digest}"
        auth = aiohttp.BasicAuth(self._config.username, self._config.password)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
                for member in tar:
                    # whiteout: 파일 삭제를 의미 → 이 레이어에서는 없음
                    if member.name.lstrip("./") == ".wh.etc/passwd":
                        return None
                    if member.name.lstrip("./") == "etc/passwd":
                        f = tar.extractfile(member)
                        if f:
                            content = f.read().decode("utf-8", errors="ignore")
                            return self._parse_passwd_for_gid(content, username)
        except Exception:
            pass
        return None

    def _parse_passwd_for_gid(self, content: str, username: str) -> Optional[int]:
        """passwd 파일 내용에서 username의 GID 추출.

        passwd 형식: username:x:uid:gid:gecos:home:shell
        """
        for line in content.splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and parts[0] == username:
                try:
                    return int(parts[3])
                except ValueError:
                    pass
        return None

    @property
    def logger(self) -> Logger:
        return self._logger

def get_harbor_config() -> HarborConfig:
    return HarborConfig()


def get_harbor_manager(
    config: HarborConfig = Depends(get_harbor_config),
    logger: Logger = Depends(get_logger),
) -> HarborManager:
    """HarborManager 인스턴스 반환 (의존성 주입용)"""
    return HarborManager(harbor_config=config, logger=logger)
