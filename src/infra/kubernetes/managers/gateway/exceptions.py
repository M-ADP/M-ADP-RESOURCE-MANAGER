"""Gateway 관련 예외 클래스"""

from typing import Any, Dict, Optional

from src.infra.kubernetes.exceptions import KubernetesResourceException


class GatewayCreationException(KubernetesResourceException):
    """Gateway 생성 실패 예외"""

    def __init__(
        self,
        gateway_name: str,
        namespace: str,
        reason: str,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            resource_type="Gateway",
            resource_name=gateway_name,
            operation="create",
            reason=reason,
            detail=detail or {"namespace": namespace},
        )
        self.gateway_name = gateway_name
        self.namespace = namespace


class GatewayReadException(KubernetesResourceException):
    """Gateway 조회 실패 예외"""

    def __init__(
        self,
        gateway_name: str,
        namespace: str,
        reason: str,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            resource_type="Gateway",
            resource_name=gateway_name,
            operation="read",
            reason=reason,
            detail=detail or {"namespace": namespace},
        )
        self.gateway_name = gateway_name
        self.namespace = namespace


class GatewayUpdateException(KubernetesResourceException):
    """Gateway 업데이트 실패 예외"""

    def __init__(
        self,
        gateway_name: str,
        namespace: str,
        reason: str,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            resource_type="Gateway",
            resource_name=gateway_name,
            operation="update",
            reason=reason,
            detail=detail or {"namespace": namespace},
        )
        self.gateway_name = gateway_name
        self.namespace = namespace


class GatewayDeletionException(KubernetesResourceException):
    """Gateway 삭제 실패 예외"""

    def __init__(
        self,
        gateway_name: str,
        namespace: str,
        reason: str,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            resource_type="Gateway",
            resource_name=gateway_name,
            operation="delete",
            reason=reason,
            detail=detail or {"namespace": namespace},
        )
        self.gateway_name = gateway_name
        self.namespace = namespace


class GatewayListException(KubernetesResourceException):
    """Gateway 목록 조회 실패 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            resource_type="Gateway",
            resource_name="*",
            operation="list",
            reason=reason,
            detail=detail or {"namespace": namespace or "all"},
        )
        self.namespace = namespace
