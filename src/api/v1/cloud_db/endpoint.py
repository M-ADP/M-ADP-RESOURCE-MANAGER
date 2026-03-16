"""Cloud DB API 라우터"""

from fastapi import APIRouter, Depends, Path

from src.api.v1.cloud_db.schemas.request import CloudDbCreateRequest, CloudDbRevisionRequest
from src.api.v1.cloud_db.schemas.response import CloudDbCreateResponse, CloudDbDeleteResponse, CloudDbRevisionResponse
from src.app.cloud_db.cloud_db_create_use_case import CloudDbCreateUseCase
from src.app.cloud_db.cloud_db_delete_use_case import CloudDbDeleteUseCase
from src.app.cloud_db.cloud_db_revision_use_case import CloudDbRevisionUseCase
from src.core.response import SuccessResponse

cloud_db_router = APIRouter(prefix="/cloud-dbs", tags=["cloud-dbs"])


@cloud_db_router.post("/{project_id}", response_model=SuccessResponse[CloudDbCreateResponse])
async def create_cloud_db(
    payload: CloudDbCreateRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    cloud_db_create_usecase: CloudDbCreateUseCase = Depends(CloudDbCreateUseCase)
):
    """Cloud DB 생성

    StatefulSet 자원을 생성합니다.
    - Headless Service 및 ClusterIP Service 자동 생성
    """
    result = await cloud_db_create_usecase(project_id=project_id, payload=payload)
    return SuccessResponse(message="Cloud DB created successfully", data=result)


@cloud_db_router.delete("/{project_id}/{name}", response_model=SuccessResponse[CloudDbDeleteResponse])
async def delete_cloud_db(
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="Cloud DB 이름 (StatefulSet 이름)"),
    cloud_db_delete_usecase: CloudDbDeleteUseCase = Depends(CloudDbDeleteUseCase)
):
    """Cloud DB 삭제

    StatefulSet 및 연관 리소스(PVC, SA, Service)를 삭제합니다.
    """
    result = await cloud_db_delete_usecase(name=name, project_id=project_id)
    return SuccessResponse(message="Cloud DB deleted successfully", data=result)


@cloud_db_router.patch("/{project_id}/{name}", response_model=SuccessResponse[CloudDbRevisionResponse])
async def revise_cloud_db(
    payload: CloudDbRevisionRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="Cloud DB 이름 (StatefulSet 이름)"),
    cloud_db_revision_usecase: CloudDbRevisionUseCase = Depends(CloudDbRevisionUseCase)
):
    """Cloud DB 리소스 수정

    StatefulSet 자원량을 수정합니다.
    - CPU, Memory 리소스 조정
    - 레플리카 수 조정
    - 디스크 확장
    """
    result = await cloud_db_revision_usecase(name=name, project_id=project_id, payload=payload)
    return SuccessResponse(message="Cloud DB revised successfully", data=result)
