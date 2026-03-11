"""ServiceAccount 관리 관련 예외 클래스"""

from typing import Optional
from src.infra.kubernetes.exceptions import ResourceCreationException


class ServiceAccountCreationException(ResourceCreationException):
    """ServiceAccount 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        service_account_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="ServiceAccount",
            resource_name=service_account_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
