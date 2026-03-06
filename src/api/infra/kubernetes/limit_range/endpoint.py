"""Kubernetes LimitRange 모니터링 API"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.infra.kubernetes.limit_range.schema import (
    LimitRangeItemInfo,
    LimitRangeInfo,
    LimitRangeListResponse,
    LimitRangeDetailResponse,
)
from src.core.response import SuccessResponse
from src.dependencies.kubernetes import get_limit_range_manager
from src.infra.kubernetes.managers.limitrange import LimitRangeManager

limit_range_router = APIRouter(
    prefix="/limit-ranges",
    tags=["kubernetes-limit-range"],
)


def _build_limit_range_info(lr) -> LimitRangeInfo:
    limits = []
    if lr.spec and lr.spec.limits:
        for item in lr.spec.limits:
            limits.append(LimitRangeItemInfo(
                type=item.type,
                default=item.default,
                default_request=item.default_request,
                max=item.max,
                min=item.min,
                max_limit_request_ratio=item.max_limit_request_ratio,
            ))

    return LimitRangeInfo(
        name=lr.metadata.name,
        namespace=lr.metadata.namespace,
        limits=limits,
        labels=lr.metadata.labels or {},
        annotations=lr.metadata.annotations or {},
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
    lr_manager: LimitRangeManager = Depends(get_limit_range_manager),
):
    """Kubernetes LimitRange 목록 조회"""
    limit_ranges = await lr_manager.list_limitranges(
        namespace=namespace,
        label_selector=label_selector,
    )

    return SuccessResponse(
        message="LimitRanges retrieved successfully",
        data=LimitRangeListResponse(
            limit_ranges=[_build_limit_range_info(lr) for lr in limit_ranges],
            total=len(limit_ranges),
        ),
    )


@limit_range_router.get("/{namespace}/{name}", response_model=SuccessResponse[LimitRangeDetailResponse])
async def get_limit_range(
    namespace: str,
    name: str,
    lr_manager: LimitRangeManager = Depends(get_limit_range_manager),
):
    """특정 LimitRange 상세 조회"""
    lr = await lr_manager.get_limitrange(name, namespace)

    if lr is None:
        raise HTTPException(
            status_code=404,
            detail=f"LimitRange '{name}' not found in namespace '{namespace}'",
        )

    return SuccessResponse(
        message="LimitRange retrieved successfully",
        data=LimitRangeDetailResponse(limit_range=_build_limit_range_info(lr)),
    )
