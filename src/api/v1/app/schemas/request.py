"""App 요청 스키마"""

from typing import Optional, List, Dict, Annotated

from pydantic import BaseModel, Field, field_validator


class ContainerResourceRequest(BaseModel):
    """컨테이너 리소스 요청 모델"""

    cpu: str = Field(default="100m", description="CPU 리소스 (예: 100m, 500m, 1)")
    memory: str = Field(default="128Mi", description="메모리 리소스 (예: 128Mi, 512Mi, 1Gi)")


class ContainerResources(BaseModel):
    """컨테이너 리소스 제한 모델"""

    requests: ContainerResourceRequest = Field(default_factory=ContainerResourceRequest)
    limits: ContainerResourceRequest = Field(default_factory=ContainerResourceRequest)


class DiskSpec(BaseModel):
    """디스크(PVC) 스펙 모델"""

    size: str = Field(..., description="디스크 크기 (예: 1Gi, 500Mi)", examples=["1Gi"])
    mount_path: str = Field(default="/data", description="마운트 경로", examples=["/data"])
    storage_class: str = Field(default="local-path", description="StorageClass 이름")


class ContainerSpec(BaseModel):
    """컨테이너 스펙 모델"""

    name: str = Field(..., min_length=1, description="컨테이너 이름", examples=["main"])
    image: str = Field(..., min_length=1, description="컨테이너 이미지", examples=["nginx:latest"])
    ports: Optional[List[Annotated[int, Field(ge=1, le=65535)]]] = Field(
        default=None,
        description="컨테이너 포트 목록 (1-65535)",
        examples=[[8080]]
    )
    resources: ContainerResources = Field(default_factory=ContainerResources)
    disk: Optional[DiskSpec] = Field(default=None, description="디스크(PVC) 설정")
    env: Optional[Dict[str, str]] = Field(default=None, description="환경 변수", examples=[{"ENV": "production"}])
    command: Optional[List[str]] = Field(default=None, description="컨테이너 실행 명령어")
    args: Optional[List[str]] = Field(default=None, description="컨테이너 실행 인자")

    @field_validator('ports')
    @classmethod
    def validate_ports(cls, v):
        if v is not None:
            # 빈 리스트는 None으로 변환
            if len(v) == 0:
                return None
            # 포트 범위 검증
            for port in v:
                if port < 1 or port > 65535:
                    raise ValueError(f"포트 번호는 1-65535 범위여야 합니다: {port}")
        return v


class AppRevisionResourceRequest(BaseModel):
    """App 리소스 수정 요청 모델"""

    cpu: Optional[str] = Field(default=None, description="CPU 리소스 (예: 100m, 500m, 1)")
    memory: Optional[str] = Field(default=None, description="메모리 리소스 (예: 128Mi, 512Mi, 1Gi)")


class AppRevisionDiskRequest(BaseModel):
    """App 디스크 수정 요청 모델 (증가만 가능)"""

    size: str = Field(..., description="새로운 디스크 크기 (증가만 가능, 예: 2Gi)")


class AppRevisionRequest(BaseModel):
    """App 수정 요청 모델 (Deployment 리소스량 수정)"""

    container_name: Optional[str] = Field(
        default=None,
        description="수정할 컨테이너 이름 (미지정시 첫 번째 컨테이너)"
    )
    requests: Optional[AppRevisionResourceRequest] = Field(
        default=None,
        description="리소스 요청량"
    )
    limits: Optional[AppRevisionResourceRequest] = Field(
        default=None,
        description="리소스 제한량"
    )
    disk: Optional[AppRevisionDiskRequest] = Field(
        default=None,
        description="디스크 크기 수정 (증가만 가능)"
    )
    replicas: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="레플리카 수"
    )


class FixedScaleRequest(BaseModel):
    """Fixed Scale 설정 요청 (고정 레플리카)"""

    replicas: int = Field(
        ...,
        ge=1,
        le=10,
        description="고정 레플리카 수"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "replicas": 3
                }
            ]
        }
    }


class AutoScaleRequest(BaseModel):
    """Auto Scale 설정 요청 (HPA 생성)"""

    min_replicas: int = Field(
        default=1,
        ge=1,
        le=10,
        description="최소 레플리카 수"
    )
    max_replicas: int = Field(
        default=5,
        ge=1,
        le=20,
        description="최대 레플리카 수"
    )
    target_cpu_utilization: int = Field(
        default=80,
        ge=1,
        le=100,
        description="CPU 사용률 기준 (%)"
    )
    target_memory_utilization: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="메모리 사용률 기준 (%) - 선택사항"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "min_replicas": 1,
                    "max_replicas": 5,
                    "target_cpu_utilization": 80,
                    "target_memory_utilization": None
                }
            ]
        }
    }


class AppCreateRequest(BaseModel):
    """App 생성 요청 모델 (Deployment 자원 생성)"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="App 이름 (Deployment 이름)",
        examples=["my-app"]
    )
    namespace: str = Field(
        ...,
        min_length=1,
        description="배포할 네임스페이스 (프로젝트)",
        examples=["my-project"]
    )
    containers: List[ContainerSpec] = Field(
        ...,
        min_length=1,
        description="컨테이너 스펙 목록"
    )
    replicas: int = Field(default=1, ge=1, le=10, description="레플리카 수")
    labels: Optional[Dict[str, str]] = Field(default=None, description="Deployment 레이블")
    annotations: Optional[Dict[str, str]] = Field(default=None, description="Deployment 어노테이션")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "my-app",
                    "namespace": "my-project",
                    "containers": [
                        {
                            "name": "main",
                            "image": "nginx:latest",
                            "ports": [80],
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "500m", "memory": "512Mi"}
                            }
                        }
                    ],
                    "replicas": 1
                }
            ]
        }
    }


class SecretCreateRequest(BaseModel):
    """Secret 생성 요청 모델"""

    name: str = Field(..., description="Secret 이름", examples=["db-credentials"])
    data: Dict[str, str] = Field(..., description="Secret 데이터")


class EnvironmentCreateRequest(BaseModel):
    """환경 변수 생성 요청 모델 (ConfigMap 생성)"""

    data: Dict[str, str] = Field(..., description="환경 변수 데이터 (key-value)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "data": {
                        "DATABASE_URL": "postgresql://localhost:5432/mydb",
                        "REDIS_HOST": "redis.example.com",
                        "LOG_LEVEL": "INFO"
                    }
                }
            ]
        }
    }


class EnvironmentUpdateRequest(BaseModel):
    """환경 변수 수정 요청 모델 (ConfigMap 데이터 교체)"""

    data: Dict[str, str] = Field(..., description="환경 변수 데이터 (key-value) - 기존 데이터를 완전히 교체")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "data": {
                        "DATABASE_URL": "postgresql://newhost:5432/newdb",
                        "REDIS_HOST": "new-redis.example.com",
                        "LOG_LEVEL": "DEBUG",
                        "NEW_VAR": "new_value"
                    }
                }
            ]
        }
    }
