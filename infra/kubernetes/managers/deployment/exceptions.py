"""Deployment 관리 관련 예외 클래스 정의"""

from typing import Optional
from infra.kubernetes.exceptions import (
    ResourceCreationException,
    ResourceReadException,
    ResourceUpdateException,
    ResourceDeletionException,
    ResourceListException,
)


class DeploymentCreationException(ResourceCreationException):
    """Deployment 생성 실패 시 발생하는 예외"""

    def __init__(
        self,
        deployment_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Deployment",
            resource_name=deployment_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class DeploymentReadException(ResourceReadException):
    """Deployment 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        deployment_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Deployment",
            resource_name=deployment_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class DeploymentUpdateException(ResourceUpdateException):
    """Deployment 업데이트 실패 시 발생하는 예외"""

    def __init__(
        self,
        deployment_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Deployment",
            resource_name=deployment_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class DeploymentDeletionException(ResourceDeletionException):
    """Deployment 삭제 실패 시 발생하는 예외"""

    def __init__(
        self,
        deployment_name: str,
        namespace: str,
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Deployment",
            resource_name=deployment_name,
            reason=reason,
            namespace=namespace,
            detail=detail,
        )


class DeploymentListException(ResourceListException):
    """Deployment 목록 조회 실패 시 발생하는 예외"""

    def __init__(
        self,
        namespace: Optional[str],
        reason: str,
        detail: Optional[dict] = None,
    ):
        super().__init__(
            resource_type="Deployment",
            reason=reason,
            namespace=namespace,
            detail=detail,
        )
