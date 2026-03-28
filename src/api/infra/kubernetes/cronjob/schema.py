from typing import Dict, List, Optional
from pydantic import BaseModel


class CronJobStatusInfo(BaseModel):
    """CronJob 상태 정보"""

    last_schedule_time: Optional[str] = None
    last_successful_time: Optional[str] = None
    active_count: int = 0


class CronJobInfo(BaseModel):
    """CronJob 정보"""

    name: str
    namespace: str
    schedule: Optional[str] = None
    suspend: bool = False
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    status: Optional[CronJobStatusInfo] = None


class CronJobListResponse(BaseModel):
    """CronJob 목록 응답"""

    cronjobs: List[CronJobInfo]
    total: int


class CronJobDetailResponse(BaseModel):
    """CronJob 상세 정보 응답"""

    cronjob: CronJobInfo


class CronJobTriggerResponse(BaseModel):
    """CronJob 즉시 실행 응답"""

    cronjob_name: str
    namespace: str
    job_name: str
    triggered_at: str
