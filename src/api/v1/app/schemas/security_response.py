from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from src.api.v1.app.schemas.event_response import EventInfo


class SecurityConfigInfo(BaseModel):
    """보안 설정 정보"""
    container_name: str
    privileged: Optional[bool] = None
    run_as_non_root: Optional[bool] = None
    allow_privilege_escalation: Optional[bool] = None
    read_only_root_filesystem: Optional[bool] = None
    capabilities_add: List[str] = []
    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None


class AppSecurityConfigResponse(BaseModel):
    """App 보안 설정 응답"""
    deployment_name: str
    namespace: str
    configs: List[SecurityConfigInfo]


class VulnerabilityInfo(BaseModel):
    """취약점 정보"""
    vulnerability_id: str  # CVE-xxxx-xxxx
    severity: str  # Critical, High, etc.
    package: str
    version: str
    fix_version: Optional[str] = None
    description: Optional[str] = None


class AppVulnerabilityResponse(BaseModel):
    """App 취약점 스캔 결과 응답"""
    deployment_name: str
    container_name: str
    image: str
    vulnerabilities: List[VulnerabilityInfo]
    summary: dict  # {"Critical": 1, "High": 5, ...}
