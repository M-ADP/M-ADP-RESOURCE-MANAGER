import re
from typing import Optional

import aiohttp

from src.core.logger import Logger
from src.infra.kubernetes.watch.models import FailureRecord

_NAMESPACE_PREFIX = "project-"
_TIMEOUT = aiohttp.ClientTimeout(total=10)

# ReplicaSet 이름에서 Deployment 이름 추출 패턴
# RS: {deployment}-{pod-template-hash(9~10 chars)}
# Pod: {deployment}-{pod-template-hash}-{random(5 chars)}
_RS_SUFFIX = re.compile(r'^(.+)-[a-z0-9]{9,10}$')
_POD_SUFFIX = re.compile(r'^(.+)-[a-z0-9]{9,10}-[a-z0-9]{5}$')


def _extract_deployment_name(record: FailureRecord) -> Optional[str]:
    """FailureRecord에서 Deployment 이름을 추출한다.

    Pod 이벤트는 app 레이블을 우선 사용하고, ReplicaSet/Pod 이름에서 해시를 제거해 폴백한다.
    """
    if record.app_label:
        return record.app_label

    name = record.object_name
    if record.object_kind == "ReplicaSet":
        m = _RS_SUFFIX.match(name)
        if m:
            return m.group(1)
    elif record.object_kind == "Pod":
        m = _POD_SUFFIX.match(name)
        if m:
            return m.group(1)

    return None


class PerformopsClient:
    """감지된 실패를 /performops/{project_id}/{app_deployment_name} 엔드포인트에 POST한다."""

    def __init__(self, base_url: str, logger: Logger):
        self._base_url = base_url.rstrip("/")
        self._logger = logger
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(timeout=_TIMEOUT)

    async def stop(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def notify(self, record: FailureRecord) -> None:
        if self._session is None:
            return

        project_id = record.namespace.removeprefix(_NAMESPACE_PREFIX)
        deployment_name = _extract_deployment_name(record)

        if not deployment_name:
            self._logger.warning(
                f"[performops] 배포 이름 추출 실패 — 호출 생략 "
                f"(namespace={record.namespace}, object={record.object_name})"
            )
            return

        url = f"{self._base_url}/performops/{project_id}/{deployment_name}"

        try:
            async with self._session.post(url) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    self._logger.warning(
                        f"[performops] 응답 오류 {resp.status} — "
                        f"url={url} body={body[:200]}"
                    )
                else:
                    self._logger.info(
                        f"[performops] 호출 성공 {resp.status} — "
                        f"project={project_id} app={deployment_name} "
                        f"failure={record.failure_type}"
                    )
        except Exception as e:
            # 알림 실패가 Watch 루프를 멈춰선 안 된다.
            self._logger.error(f"[performops] 호출 실패: {e}")
