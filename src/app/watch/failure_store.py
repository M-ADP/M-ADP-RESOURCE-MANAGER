from collections import deque
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from src.infra.kubernetes.watch.models import FailureRecord, FailureType

_DEFAULT_TTL_SECONDS = 3600
_DEFAULT_MAX_RECORDS = 500


class FailureStore:
    """
    Watch에서 감지된 실패 레코드를 TTL 기반 in-memory deque에 보관한다.

    asyncio 단일 스레드에서만 접근되므로 별도 잠금이 필요 없다.
    maxlen으로 메모리 상한을 보장한다.
    """

    def __init__(
        self,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        max_records: int = _DEFAULT_MAX_RECORDS,
    ):
        self._ttl = timedelta(seconds=ttl_seconds)
        self._records: deque[FailureRecord] = deque(maxlen=max_records)

    def add(self, record: FailureRecord) -> None:
        self._records.append(record)

    def query(
        self,
        namespace: Optional[str] = None,
        failure_type: Optional[FailureType] = None,
        since_seconds: Optional[int] = None,
    ) -> List[FailureRecord]:
        now = datetime.now(timezone.utc)
        ttl_cutoff = now - self._ttl

        result = []
        for r in self._records:
            if r.detected_at < ttl_cutoff:
                continue
            if namespace is not None and r.namespace != namespace:
                continue
            if failure_type is not None and r.failure_type != failure_type:
                continue
            if since_seconds is not None:
                if (now - r.detected_at).total_seconds() > since_seconds:
                    continue
            result.append(r)

        return sorted(result, key=lambda r: r.detected_at, reverse=True)
