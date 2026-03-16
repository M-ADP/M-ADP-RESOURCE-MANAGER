"""DNS API 응답 스키마"""

from pydantic import BaseModel, Field


class DnsCreateResponse(BaseModel):
    """DNS 레코드 생성 응답"""

    id: str = Field(..., description="DNS 레코드 식별자")
    project_id: str = Field(..., description="프로젝트 ID")
    deployment_id: str = Field(..., description="대상 Deployment 이름")
    subdomain: str = Field(..., description="서브도메인 슬러그")
    hostname: str = Field(..., description="생성된 전체 도메인")


class DnsUpdateResponse(BaseModel):
    """DNS 서브도메인 수정 응답"""

    id: str = Field(..., description="DNS 레코드 식별자")
    project_id: str = Field(..., description="프로젝트 ID")
    deployment_id: str = Field(..., description="대상 Deployment 이름")
    subdomain: str = Field(..., description="변경된 서브도메인 슬러그")
    hostname: str = Field(..., description="변경된 전체 도메인")


class DnsDeleteResponse(BaseModel):
    """DNS 레코드 삭제 응답"""

    id: str = Field(..., description="삭제된 DNS 레코드 식별자")
    deleted: bool = Field(..., description="삭제 성공 여부")
