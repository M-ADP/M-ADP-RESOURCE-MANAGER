from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ContainerStateInfo(BaseModel):
    """Container 상태 정보"""

    state: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None
    reason: Optional[str] = None
    message: Optional[str] = None


class ContainerStatusInfo(BaseModel):
    """Container 상태 정보"""

    name: str
    ready: bool
    restart_count: int
    image: str
    state: ContainerStateInfo


class PodConditionInfo(BaseModel):
    """Pod Condition 정보"""

    type: str
    status: str
    reason: Optional[str] = None
    message: Optional[str] = None


class PodStatusInfo(BaseModel):
    """Pod 상태 정보"""

    phase: Optional[str] = None
    pod_ip: Optional[str] = None
    host_ip: Optional[str] = None
    start_time: Optional[str] = None
    conditions: List[PodConditionInfo] = []
    container_statuses: List[ContainerStatusInfo] = []


class PodInfo(BaseModel):
    """Pod 정보"""

    name: str
    namespace: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    status: Optional[PodStatusInfo] = None


class PodListResponse(BaseModel):
    """Pod 목록 응답"""

    pods: List[PodInfo]
    total: int


class PodDetailResponse(BaseModel):
    """Pod 상세 정보 응답"""

    pod: PodInfo


class PodLogsResponse(BaseModel):
    """Pod 로그 응답"""

    pod_name: str
    namespace: str
    container: Optional[str] = None
    logs: str


class PodDeleteResponse(BaseModel):
    """Pod 삭제 응답"""

    name: str
    namespace: str
    deleted: bool
