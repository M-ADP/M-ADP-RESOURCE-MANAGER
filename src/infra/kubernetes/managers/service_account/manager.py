"""ServiceAccount 리소스 관리 클래스"""

import base64
import json
from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1Secret,
    V1ServiceAccount,
    V1ObjectMeta,
    V1LocalObjectReference,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from src.infra.kubernetes.managers.namespace import NamespaceNotFoundException
from .exceptions import ServiceAccountCreationException


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
            
            if e.status == 404:
                self.logger.error(f"Namespace 미발견: {namespace}")
                raise NamespaceNotFoundException(namespace_name=namespace)

            self.logger.error(f"ServiceAccount 생성 실패: {name} - {e.reason}")
            raise ServiceAccountCreationException(
                service_account_name=name,
                namespace=namespace,
                reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )

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

    async def create_docker_registry_secret(
        self,
        name: str,
        namespace: str,
        registry: str,
        username: str,
        password: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> V1Secret:
        """Namespace에 docker-registry 타입 Secret 생성 (imagePullSecret 용도)"""
        self.logger.info(f"docker-registry Secret 생성 시도: {name} (namespace: {namespace})")

        try:
            existing = await self.k8s_client.core_v1.read_namespaced_secret(
                name=name, namespace=namespace
            )
            self.logger.info(f"docker-registry Secret 이미 존재: {name} (namespace: {namespace})")
            return existing
        except ApiException as e:
            if e.status != 404:
                raise

        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        docker_config = {
            "auths": {
                registry: {
                    "username": username,
                    "password": password,
                    "auth": auth,
                }
            }
        }
        encoded = base64.b64encode(json.dumps(docker_config).encode()).decode()

        secret = V1Secret(
            metadata=V1ObjectMeta(name=name, namespace=namespace, labels=labels),
            type="kubernetes.io/dockerconfigjson",
            data={".dockerconfigjson": encoded},
        )

        created = await self.k8s_client.core_v1.create_namespaced_secret(
            namespace=namespace, body=secret
        )
        self.logger.info(f"docker-registry Secret 생성 완료: {name} (namespace: {namespace})")
        return created

    async def delete_docker_registry_secret(self, name: str, namespace: str) -> bool:
        """docker-registry Secret 삭제"""
        try:
            await self.k8s_client.core_v1.delete_namespaced_secret(
                name=name, namespace=namespace
            )
            return True
        except ApiException as e:
            if e.status == 404:
                return True
            raise
