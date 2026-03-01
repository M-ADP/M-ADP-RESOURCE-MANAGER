from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Pod:
    """Pod 도메인 모델"""
    name: str
    namespace: str
    phase: Optional[str] = None


@dataclass
class PodLogs:
    """Pod 로그 도메인 모델"""
    pod_name: str
    namespace: str
    logs: str


@dataclass
class Event:
    """Kubernetes Event 도메인 모델"""
    type: str  # Normal, Warning
    reason: str
    message: str
    involved_object_kind: str
    involved_object_name: str
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    count: Optional[int] = None
