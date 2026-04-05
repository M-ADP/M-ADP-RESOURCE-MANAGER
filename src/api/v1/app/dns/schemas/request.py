"""DNS API 요청 스키마"""

from pydantic import BaseModel, Field


class DnsCreateRequest(BaseModel):
    """DNS 레코드 생성 요청"""

    id: str = Field(..., description="DNS 레코드 식별자 (플랫폼 DB ID)")
    project_id: str = Field(..., description="프로젝트 ID")
    deployment_id: str = Field(..., description="대상 Deployment의 플랫폼 ID (x-app-deployment-id 레이블로 탐색)")
    subdomain: str = Field(
        ...,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
        description="서브도메인 슬러그 (예: my-app)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "123",
                "project_id": "456",
                "deployment_id": "my-app",
                "subdomain": "my-app",
            }]
        }
    }


class DnsUpdateRequest(BaseModel):
    """DNS 서브도메인 수정 요청"""

    project_id: str = Field(..., description="프로젝트 ID")
    deployment_id: str = Field(..., description="대상 Deployment 이름")
    subdomain: str = Field(
        ...,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
        description="변경할 서브도메인 슬러그",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "project_id": "456",
                "deployment_id": "my-app",
                "subdomain": "new-app",
            }]
        }
    }
