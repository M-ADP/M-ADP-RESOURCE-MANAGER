"""App 응답 스키마"""

from typing import Optional, List, Dict

from pydantic import BaseModel, Field


class ContainerInfo(BaseModel):
    """컨테이너 정보 응답 모델"""

    name: str
    image: str


class DeploymentStatusInfo(BaseModel):
    """Deployment 상태 정보 응답 모델"""

    replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    available_replicas: Optional[int] = None
    updated_replicas: Optional[int] = None


class AppCreateResponse(BaseModel):
    """App 생성 응답 모델"""

    name: str = Field(..., description="생성된 App 이름")
    namespace: str = Field(..., description="네임스페이스")
    replicas: int = Field(..., description="레플리카 수")
    containers: List[ContainerInfo] = Field(..., description="컨테이너 목록")
    labels: Optional[Dict[str, str]] = Field(default=None, description="레이블")
    status: Optional[DeploymentStatusInfo] = Field(default=None, description="Deployment 상태")
