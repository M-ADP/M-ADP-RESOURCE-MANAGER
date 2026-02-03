"""ServiceAccount 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1ServiceAccount,
    V1ObjectMeta,
    V1LocalObjectReference,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger


class ServiceAccountManager:
    """ServiceAccount 리소스를 관리하는 클래스"""

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_service_account(
        self,
        name: str,
        namespace: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        image_pull_secrets: Optional[List[str]] = None,
    ) -> V1ServiceAccount:
        """ServiceAccount 비동기 생성"""
        self.logger.info(f"ServiceAccount 생성 시도: {name} (namespace: {namespace})")

        existing = await self.get_service_account(name, namespace)
        if existing:
            self.logger.info(f"ServiceAccount 이미 존재함: {name} (namespace: {namespace})")
            return existing

        body = V1ServiceAccount(
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels,
                annotations=annotations,
            )
        )

        if image_pull_secrets:
            body.image_pull_secrets = [
                V1LocalObjectReference(name=s) for s in image_pull_secrets
            ]

        try:
            sa = await self.k8s_client.core_v1.create_namespaced_service_account(
                namespace=namespace,
                body=body,
            )
            self.logger.info(f"ServiceAccount 생성 완료: {name} (namespace: {namespace})")
            return sa
        except ApiException as e:
            if e.status == 409:
                return await self.get_service_account(name, namespace)
            self.logger.error(f"ServiceAccount 생성 실패: {name} - {e.reason}")
            raise e

    async def get_service_account(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1ServiceAccount]:
        """ServiceAccount 비동기 조회"""
        try:
            return await self.k8s_client.core_v1.read_namespaced_service_account(
                name=name,
                namespace=namespace,
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise e

    async def delete_service_account(
        self,
        name: str,
        namespace: str,
    ) -> bool:
        """ServiceAccount 비동기 삭제"""
        try:
            await self.k8s_client.core_v1.delete_namespaced_service_account(
                name=name,
                namespace=namespace,
            )
            return True
        except ApiException as e:
            if e.status == 404:
                return True
            raise e

    async def list_service_accounts(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[V1ServiceAccount]:
        """ServiceAccount 목록 조회"""
        try:
            if namespace:
                result = await self.k8s_client.core_v1.list_namespaced_service_account(
                    namespace=namespace,
                    label_selector=label_selector,
                )
            else:
                result = await self.k8s_client.core_v1.list_service_account_for_all_namespaces(
                    label_selector=label_selector,
                )
            return result.items
        except ApiException as e:
            self.logger.error(f"ServiceAccount 목록 조회 실패 - {e.reason}")
            raise e

    async def exists(self, name: str, namespace: str) -> bool:
        """ServiceAccount 존재 여부 확인"""
        sa = await self.get_service_account(name, namespace)
        return sa is not None
