"""Kubernetes LimitRange 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.limit_range.schema import (
    LimitRangeItemInfo,
    LimitRangeInfo,
    LimitRangeListResponse,
    LimitRangeDetailResponse,
)
from src.core.kubernetes.limit_range import LimitRangeRepository
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_limit_range_repository

limit_range_router = APIRouter(
    prefix="/limit-ranges",
    tags=["kubernetes-limit-range"],
)


@limit_range_router.get("", response_model=SuccessResponse[LimitRangeListResponse])
async def list_limit_ranges(
    namespace: Optional[str] = Query(
        default=None,
        description="Filter by namespace",
    ),
    label_selector: Optional[str] = Query(
        default=None,
        description="Label selector",
    ),
    lr_repo: LimitRangeRepository = Depends(get_limit_range_repository),
):
    """Kubernetes LimitRange 목록 조회"""
    limit_ranges = await lr_repo.find_all(
        namespace=namespace,
        label_selector=label_selector,
    )

    lr_infos = [
        LimitRangeInfo(
            name=lr.name,
            namespace=lr.namespace,
            limits=[
                LimitRangeItemInfo(
                    type=item.type,
                    default=item.default,
                    default_request=item.default_request,
                    max=item.max,
                    min=item.min,
                    max_limit_request_ratio=item.max_limit_request_ratio,
                )
                for item in lr.limits
            ],
            labels=lr.labels,
            annotations=lr.annotations,
        )
        for lr in limit_ranges
    ]

    return SuccessResponse(
        message="LimitRanges retrieved successfully",
        data=LimitRangeListResponse(
            limit_ranges=lr_infos,
            total=len(lr_infos),
        ),
    )


@limit_range_router.get("/{namespace}/{name}", response_model=SuccessResponse[LimitRangeDetailResponse])
async def get_limit_range(
    namespace: str,
    name: str,
    lr_repo: LimitRangeRepository = Depends(get_limit_range_repository),
):
    """특정 LimitRange 상세 조회"""
    lr = await lr_repo.find_by_name(name, namespace)

    if lr is None:
        raise HTTPException(
            status_code=404,
            detail=f"LimitRange '{name}' not found in namespace '{namespace}'",
        )

    lr_info = LimitRangeInfo(
        name=lr.name,
        namespace=lr.namespace,
        limits=[
            LimitRangeItemInfo(
                type=item.type,
                default=item.default,
                default_request=item.default_request,
                max=item.max,
                min=item.min,
                max_limit_request_ratio=item.max_limit_request_ratio,
            )
            for item in lr.limits
        ],
        labels=lr.labels,
        annotations=lr.annotations,
    )

    return SuccessResponse(
        message="LimitRange retrieved successfully",
        data=LimitRangeDetailResponse(limit_range=lr_info),
    )
