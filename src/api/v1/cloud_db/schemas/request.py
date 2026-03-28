"""Cloud DB 요청 스키마"""

from enum import Enum
from typing import Optional, List, Dict

from pydantic import BaseModel, Field

from pydantic import field_validator

from src.api.v1.app.schemas.request import (
    AppRevisionRequest as CloudDBRevisionRequest,
    ContainerSpec,
    ContainerResources,
    DiskSpec,
)


class CloudDBType(str, Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"


CLOUD_DB_IMAGES: Dict[CloudDBType, str] = {
    CloudDBType.MYSQL: "mysql:8.4",
    CloudDBType.POSTGRESQL: "postgres:17",
}

CLOUD_DB_DEFAULT_PORTS: Dict[CloudDBType, List[int]] = {
    CloudDBType.MYSQL: [3306],
    CloudDBType.POSTGRESQL: [5432],
}

CLOUD_DB_MOUNT_PATHS: Dict[CloudDBType, str] = {
    CloudDBType.MYSQL: "/var/lib/mysql",
    CloudDBType.POSTGRESQL: "/var/lib/postgresql/data",
}


class CloudDBDiskSpec(BaseModel):
    """Cloud DB 디스크 스펙 (mount_path는 type에서 자동 결정)"""

    size: str = Field(..., description="디스크 크기 (예: 1024Mi)", examples=["1024Mi"])
    storage_class: str = Field(default="linstor-pv-fast", description="StorageClass 이름")


class CloudDBContainerSpec(ContainerSpec):
    """Cloud DB 컨테이너 스펙 (image, disk.mount_path는 type으로부터 자동 결정)"""

    image: Optional[str] = Field(
        default=None,
        description="컨테이너 이미지 (미지정 시 type에서 자동 결정)",
    )
    disk: Optional[CloudDBDiskSpec] = Field(default=None, description="디스크(PVC) 설정")


class CloudDBCreateRequest(BaseModel):
    """Cloud DB 생성 요청 모델"""

    type: CloudDBType = Field(
        ...,
        description="DB 종류 (mysql | postgresql)",
        examples=["mysql"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="Cloud DB 이름 (StatefulSet 이름)",
        examples=["my-db"],
    )
    containers: List[CloudDBContainerSpec] = Field(
        default_factory=list,
        description="컨테이너 스펙 목록 (미지정 시 type 기본값으로 자동 구성)",
    )
    replicas: int = Field(default=1, ge=1, le=10, description="레플리카 수")
    labels: Optional[Dict[str, str]] = Field(default=None, description="레이블")
    annotations: Optional[Dict[str, str]] = Field(default=None, description="어노테이션")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "mysql",
                    "name": "my-db",
                    "replicas": 1,
                    "containers": [
                        {
                            "name": "main",
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "500m", "memory": "512Mi"},
                            },
                            "disk": {
                                "size": "1024Mi",
                            },
                        }
                    ],
                }
            ]
        }
    }


class CloudDBQueryRequest(BaseModel):
    """Cloud DB 쿼리 실행 요청"""

    sql: str = Field(..., min_length=1, description="실행할 SQL 쿼리")
    container_name: Optional[str] = Field(
        default=None,
        description="실행할 컨테이너 이름 (미지정 시 첫 번째 컨테이너)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{"sql": "SELECT 1"}]
        }
    }


__all__ = [
    "CloudDBType",
    "CloudDBDiskSpec",
    "CloudDBContainerSpec",
    "CLOUD_DB_IMAGES",
    "CLOUD_DB_DEFAULT_PORTS",
    "CLOUD_DB_MOUNT_PATHS",
    "CloudDBCreateRequest",
    "CloudDBRevisionRequest",
    "CloudDBQueryRequest",
]
