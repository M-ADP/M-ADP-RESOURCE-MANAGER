from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class FailureType(str, Enum):
    FAILED_CREATE = "FAILED_CREATE"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    IMAGE_PULL_BACKOFF = "IMAGE_PULL_BACKOFF"
    OOM_KILLED = "OOM_KILLED"
    CRASH_LOOP_BACKOFF = "CRASH_LOOP_BACKOFF"
    ROLLOUT_STALL = "ROLLOUT_STALL"


@dataclass
class WatcherState:
    name: str
    is_running: bool = False
    restart_count: int = 0
    last_event_at: Optional[datetime] = None
    last_error: Optional[str] = None


@dataclass
class FailureRecord:
    namespace: str
    failure_type: FailureType
    reason: str
    message: str
    object_kind: str
    object_name: str
    app_label: Optional[str] = None
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
