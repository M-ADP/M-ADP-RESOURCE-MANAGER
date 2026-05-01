import asyncio
from typing import Optional

import aiohttp

from src.core.logger import Logger
from src.infra.kubernetes.watch.models import FailureRecord

_NAMESPACE_PREFIX = "project-"
_TIMEOUT = aiohttp.ClientTimeout(total=60)


def _extract_deployment_name(record: FailureRecord) -> Optional[str]:
    """FailureRecord에서 Deployment 이름을 추출한다.

    우선순위:
    1. app_label — PodWatcher가 Pod labels에서 직접 추출한 값
    2. object_kind == Deployment — object_name 자체가 Deployment 이름
    3. object_kind == ReplicaSet — {deployment}-{hash} 에서 마지막 세그먼트 제거
    4. object_kind == Pod — {deployment}-{hash}-{suffix} 에서 마지막 두 세그먼트 제거

    정규식 대신 rsplit을 사용한다.
    K8s hash charset(bcdfghjklmnpqrstvwxz2456789)은 고정되지 않아 정규식이 불안정하다.
    """
    if record.app_label:
        return record.app_label

    name = record.object_name
    if not name:
        return None

    if record.object_kind == "Deployment":
        return name

    if record.object_kind == "ReplicaSet":
        # {deployment-name}-{pod-template-hash}
        parts = name.rsplit("-", 1)
        if len(parts) == 2 and parts[0]:
            return parts[0]

    if record.object_kind == "Pod":
        # {deployment-name}-{pod-template-hash}-{random-suffix}
        parts = name.rsplit("-", 2)
        if len(parts) == 3 and parts[0]:
            return parts[0]

    return None


class PerformopsClient:
    """감지된 실패를 /performops/{project_id}/{app_deployment_name} 엔드포인트에 POST한다."""

    def __init__(self, base_url: str, logger: Logger):
        self._base_url = base_url.rstrip("/")
        self._logger = logger
        self._session: Optional[aiohttp.ClientSession] = None
        self._inflight: set[str] = set()

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(timeout=_TIMEOUT)

    async def stop(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def notify(self, record: FailureRecord) -> None:
        """실패 알림을 비동기로 발송한다.

        같은 (project_id, deployment_name) 조합으로 이미 요청이 처리 중이면
        새 요청을 차단해 PerformOps DB 커넥션 풀 고갈을 방지한다.
        """
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

        key = f"{project_id}/{deployment_name}"
        if key in self._inflight:
            self._logger.info(
                f"[performops] 중복 요청 차단 — {key} 이미 처리 중"
            )
            return

        self._inflight.add(key)
        asyncio.create_task(
            self._send(key, project_id, deployment_name, record.failure_type),
            name=f"performops-{key}",
        )

    async def _send(self, key: str, project_id: str, deployment_name: str, failure_type) -> None:
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
                        f"failure={failure_type}"
                    )
        except Exception as e:
            self._logger.error(f"[performops] 호출 실패: {e}")
        finally:
            self._inflight.discard(key)
