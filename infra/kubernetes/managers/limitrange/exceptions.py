"""LimitRange 관리 관련 예외 클래스 정의"""

from typing import Optional
from infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class LimitRangeCreationException(ResourceCreationException):
    """LimitRange 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        limitrange_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="LimitRange",
            resource_name=limitrange_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class LimitRangeReadException(ResourceReadException):
    """LimitRange 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        limitrange_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="LimitRange",
            resource_name=limitrange_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class LimitRangeUpdateException(ResourceUpdateException):
    """LimitRange 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        limitrange_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="LimitRange",
            resource_name=limitrange_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class LimitRangeDeletionException(ResourceDeletionException):
    """LimitRange 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        limitrange_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="LimitRange",
            resource_name=limitrange_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class LimitRangeListException(ResourceListException):
    """LimitRange 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="LimitRange",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
