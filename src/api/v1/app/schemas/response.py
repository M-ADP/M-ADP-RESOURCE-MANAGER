"""App 응답 스키마"""

from typing import Optional, List, Dict

from pydantic import BaseModel, Field


class PvcInfo(BaseModel):
    """PVC 정보 응답 모델"""

    name: str
    size: str
    mount_path: str
    storage_class: Optional[str] = None
    phase: Optional[str] = None


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
    pvcs: List[PvcInfo] = Field(default_factory=list, description="PVC 목록")
    labels: Optional[Dict[str, str]] = Field(default=None, description="레이블")
    status: Optional[DeploymentStatusInfo] = Field(default=None, description="Deployment 상태")


class AppDeleteResponse(BaseModel):
    """App 삭제 응답 모델"""

    name: str = Field(..., description="삭제된 App 이름")
    namespace: str = Field(..., description="네임스페이스")
    deleted: bool = Field(..., description="삭제 성공 여부")


class ContainerResourceInfo(BaseModel):
    """컨테이너 리소스 정보 응답 모델"""

    cpu: Optional[str] = None
    memory: Optional[str] = None


class ContainerResourcesInfo(BaseModel):
    """컨테이너 리소스 정보 응답 모델"""

    requests: Optional[ContainerResourceInfo] = None
    limits: Optional[ContainerResourceInfo] = None


class AppRevisionResponse(BaseModel):
    """App 수정 응답 모델"""

    name: str = Field(..., description="수정된 App 이름")
    namespace: str = Field(..., description="네임스페이스")
    replicas: int = Field(..., description="레플리카 수")
    container_name: str = Field(..., description="수정된 컨테이너 이름")
    resources: ContainerResourcesInfo = Field(..., description="수정된 리소스 정보")
    pvc: Optional[PvcInfo] = Field(default=None, description="PVC 정보")


class FixedScaleResponse(BaseModel):
    """Fixed Scale 설정 응답 모델"""

    name: str = Field(..., description="Deployment 이름")
    namespace: str = Field(..., description="네임스페이스")
    replicas: int = Field(..., description="고정 레플리카 수")
    hpa_deleted: bool = Field(..., description="HPA 삭제 여부")


class AutoScaleResponse(BaseModel):
    """Auto Scale 설정 응답 모델 (HPA)"""

    name: str = Field(..., description="HPA 이름")
    namespace: str = Field(..., description="네임스페이스")
    deployment_name: str = Field(..., description="대상 Deployment 이름")
    min_replicas: int = Field(..., description="최소 레플리카 수")
    max_replicas: int = Field(..., description="최대 레플리카 수")
    target_cpu_utilization: Optional[int] = Field(default=None, description="CPU 사용률 기준 (%)")
    target_memory_utilization: Optional[int] = Field(default=None, description="메모리 사용률 기준 (%)")
    current_replicas: Optional[int] = Field(default=None, description="현재 레플리카 수")
    desired_replicas: Optional[int] = Field(default=None, description="목표 레플리카 수")


class SecretCreateResponse(BaseModel):
    """Secret 생성 응답 모델"""

    name: str = Field(..., description="Secret 이름")
    namespace: str = Field(..., description="네임스페이스")
    app_name: str = Field(..., description="App 이름")
    path: str = Field(..., description="Vault 경로")
    policy_name: str = Field(..., description="생성된 Policy 이름")
    role_name: str = Field(..., description="생성된 Role 이름")


class SecretDeleteResponse(BaseModel):
    """Secret 삭제 응답 모델"""

    name: str = Field(..., description="삭제된 Secret 이름")
    path: str = Field(..., description="삭제된 Vault 경로")
    all_secrets_deleted: bool = Field(..., description="해당 앱의 모든 Secret 삭제 및 권한 정리 여부")


class EnvironmentCreateResponse(BaseModel):
    """환경 변수 생성 응답 모델"""

    name: str = Field(..., description="생성된 ConfigMap 이름")
    namespace: str = Field(..., description="네임스페이스")
    app_name: str = Field(..., description="App 이름")
    data_keys: List[str] = Field(..., description="생성된 환경 변수 키 목록")


class EnvironmentUpdateResponse(BaseModel):
    """환경 변수 수정 응답 모델"""

    name: str = Field(..., description="수정된 ConfigMap 이름")
    namespace: str = Field(..., description="네임스페이스")
    app_name: str = Field(..., description="App 이름")
    data_keys: List[str] = Field(..., description="수정된 환경 변수 키 목록")
