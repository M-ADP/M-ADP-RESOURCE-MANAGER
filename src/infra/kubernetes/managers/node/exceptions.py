"""Node 관리 관련 예외 클래스 정의"""

from typing import Optional
from src.infra.kubernetes.exceptions import (
    ResourceReadException,
    ResourceListException,
)


class NodeReadException(ResourceReadException):
    """Node 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        node_name: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Node",
            resource_name=node_name,
            reason=reason,
            namespace=None,  # Nodes are cluster-scoped
            detail=detail,
        )


class NodeListException(ResourceListException):
    """Node 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Node",
            reason=reason,
            namespace=None,
            detail=detail,
        )
