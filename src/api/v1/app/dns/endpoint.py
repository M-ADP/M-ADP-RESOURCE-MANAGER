"""DNS API 엔드포인트"""

from fastapi import APIRouter, Depends, Path

from src.api.v1.app.dns.schemas.request import DnsCreateRequest, DnsUpdateRequest
from src.api.v1.app.dns.schemas.response import DnsCreateResponse, DnsDeleteResponse, DnsUpdateResponse
from src.app.dns.dns_create_use_case import DnsCreateUseCase
from src.app.dns.dns_delete_use_case import DnsDeleteUseCase
from src.app.dns.dns_update_use_case import DnsUpdateUseCase
from src.core.response import SuccessResponse

dns_router = APIRouter(prefix="/apps/dns", tags=["dns"])


@dns_router.post("", response_model=SuccessResponse[DnsCreateResponse])
async def create_dns(
    payload: DnsCreateRequest,
    use_case: DnsCreateUseCase = Depends(DnsCreateUseCase),
):
    """DNS 레코드 생성

    - Kubernetes Service(ClusterIP) 생성
    - Istio VirtualService 생성
    - Cloudflare CNAME 레코드 생성
    """
    result = await use_case(payload)
    return SuccessResponse(message="DNS record created successfully", data=result)


@dns_router.put("/{id}", response_model=SuccessResponse[DnsUpdateResponse])
async def update_dns(
    payload: DnsUpdateRequest,
    id: str = Path(..., description="DNS 레코드 식별자"),
    use_case: DnsUpdateUseCase = Depends(DnsUpdateUseCase),
):
    """DNS 서브도메인 수정

    - 기존 Cloudflare CNAME 삭제 후 새 CNAME 생성
    - VirtualService hosts 업데이트
    """
    result = await use_case(dns_id=id, payload=payload)
    return SuccessResponse(message="DNS record updated successfully", data=result)


@dns_router.delete("/{id}", response_model=SuccessResponse[DnsDeleteResponse])
async def delete_dns(
    id: str = Path(..., description="DNS 레코드 식별자"),
    use_case: DnsDeleteUseCase = Depends(DnsDeleteUseCase),
):
    """DNS 레코드 삭제

    - Cloudflare CNAME 삭제
    - Istio VirtualService 삭제
    - Kubernetes Service 삭제
    """
    result = await use_case(dns_id=id)
    return SuccessResponse(message="DNS record deleted successfully", data=result)
