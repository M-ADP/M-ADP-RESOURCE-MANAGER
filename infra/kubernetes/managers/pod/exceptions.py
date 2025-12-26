"""Pod 관리 관련 예외 클래스 정의"""

from typing import Optional
from infra.kubernetes.exceptions import (
    ResourceReadException,
    ResourceListException,
)


class PodReadException(ResourceReadException):
    """Pod 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        pod_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Pod",
            resource_name=pod_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class PodListException(ResourceListException):
    """Pod 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Pod",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
