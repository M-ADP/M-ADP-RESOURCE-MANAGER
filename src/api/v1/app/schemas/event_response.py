from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class EventInfo(BaseModel):
    """이벤트 정보"""
    type: str  # Normal, Warning
    reason: str
    message: str
    involved_object_kind: str
    involved_object_name: str
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    count: Optional[int] = None


class AppEventsResponse(BaseModel):
    """App 이벤트 응답"""
    deployment_name: str
    namespace: str
    events: List[EventInfo]
