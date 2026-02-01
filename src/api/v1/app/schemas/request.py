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
    replicas: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="레플리카 수"
    )


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
