"""Job 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class JobCreationException(ResourceCreationException):
    """Job 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        job_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Job",
            resource_name=job_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class JobReadException(ResourceReadException):
    """Job 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        job_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Job",
            resource_name=job_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class JobUpdateException(ResourceUpdateException):
    """Job 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        job_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Job",
            resource_name=job_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class JobDeletionException(ResourceDeletionException):
    """Job 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        job_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Job",
            resource_name=job_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class JobListException(ResourceListException):
    """Job 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Job",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
