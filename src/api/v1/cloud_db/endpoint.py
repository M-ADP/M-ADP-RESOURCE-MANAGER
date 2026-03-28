"""Cloud DB API 라우터"""

from fastapi import APIRouter, Depends, Path, Query

from src.api.v1.cloud_db.schemas.request import CloudDBCreateRequest, CloudDBRevisionRequest, CloudDBQueryRequest
from src.api.v1.cloud_db.schemas.response import CloudDbCreateResponse, CloudDbDeleteResponse, CloudDbRevisionResponse, CloudDbQueryResponse
from src.app.cloud_db.cloud_db_create_use_case import CloudDbCreateUseCase
from src.app.cloud_db.cloud_db_delete_use_case import CloudDbDeleteUseCase
from src.app.cloud_db.cloud_db_revision_use_case import CloudDbRevisionUseCase
from src.app.cloud_db.cloud_db_query_use_case import CloudDbQueryUseCase
from src.api.v1.cloud_db.schemas.request import CloudDBType
from src.core.response import SuccessResponse

cloud_db_router = APIRouter(prefix="/cloud-dbs", tags=["cloud-dbs"])


@cloud_db_router.post("/{project_id}", response_model=SuccessResponse[CloudDbCreateResponse])
async def create_cloud_db(
    payload: CloudDBCreateRequest,
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
    payload: CloudDBRevisionRequest,
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


@cloud_db_router.post("/{project_id}/{name}/query", response_model=SuccessResponse[CloudDbQueryResponse])
async def query_cloud_db(
    payload: CloudDBQueryRequest,
    project_id: str = Path(..., description="프로젝트 ID"),
    name: str = Path(..., description="Cloud DB 이름 (StatefulSet 이름)"),
    db_type: CloudDBType = Query(..., description="DB 종류 (mysql | postgresql)"),
    cloud_db_query_usecase: CloudDbQueryUseCase = Depends(CloudDbQueryUseCase),
):
    """Cloud DB 쿼리 실행

    StatefulSet Pod에 직접 SQL 쿼리를 실행하고 결과를 반환합니다.
    """
    result = await cloud_db_query_usecase(
        project_id=project_id,
        name=name,
        db_type=db_type,
        payload=payload,
    )
    return SuccessResponse(message="Query executed successfully", data=result)
