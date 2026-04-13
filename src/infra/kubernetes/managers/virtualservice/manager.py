"""Istio VirtualService 리소스 관리 클래스"""

from typing import Any, Dict, List, Optional

from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    VirtualServiceCreationException,
    VirtualServiceReadException,
    VirtualServiceDeletionException,
)

ISTIO_VS_GROUP = "networking.istio.io"
ISTIO_VS_VERSION = "v1beta1"
ISTIO_VS_PLURAL = "virtualservices"


class IstioVirtualServiceManager:
    """Istio VirtualService CRD를 관리하는 클래스"""

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_virtualservice(
        self,
        name: str,
        namespace: str,
        hosts: List[str],
        gateways: List[str],
        http_routes: List[Dict[str, Any]],
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Istio VirtualService 생성.

        Args:
            name: VirtualService 이름
            namespace: 네임스페이스
            hosts: 라우팅 대상 호스트명 목록
            gateways: 연결할 Gateway 이름 목록
            http_routes: HTTP 라우팅 규칙 목록
                예) [{"route": [{"destination": {"host": "svc", "port": {"number": 80}}}]}]
            labels: 레이블
            annotations: 어노테이션

        Returns:
            생성된 VirtualService dict

        Raises:
            VirtualServiceCreationException
        """
        self.logger.info(f"VirtualService 생성 시도: {name} (namespace: {namespace})")

        existing = await self.get_virtualservice(name, namespace)
        if existing:
            self.logger.info(f"VirtualService 이미 존재함: {name} (namespace: {namespace})")
            return existing

        body = {
            "apiVersion": f"{ISTIO_VS_GROUP}/{ISTIO_VS_VERSION}",
            "kind": "VirtualService",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": labels or {},
                "annotations": annotations or {},
            },
            "spec": {
                "hosts": hosts,
                "gateways": gateways,
                "http": http_routes,
            },
        }

        try:
            result = await self.k8s_client.custom_objects.create_namespaced_custom_object(
                group=ISTIO_VS_GROUP,
                version=ISTIO_VS_VERSION,
                namespace=namespace,
                plural=ISTIO_VS_PLURAL,
                body=body,
            )
            self.logger.info(f"VirtualService 생성 완료: {name} (namespace: {namespace})")
            return result

        except ApiException as e:
            if e.status == 409:
                existing = await self.get_virtualservice(name, namespace)
                if existing:
                    return existing
            self.logger.error(f"VirtualService 생성 실패: {name} - {e.reason}")
            raise VirtualServiceCreationException(
                name=name, namespace=namespace, reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"VirtualService 생성 중 예외: {name} - {e}")
            raise VirtualServiceCreationException(name=name, namespace=namespace, reason=str(e))

    async def get_virtualservice(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        """VirtualService 조회. 없으면 None 반환."""
        try:
            return await self.k8s_client.custom_objects.get_namespaced_custom_object(
                group=ISTIO_VS_GROUP,
                version=ISTIO_VS_VERSION,
                namespace=namespace,
                plural=ISTIO_VS_PLURAL,
                name=name,
            )
        except ApiException as e:
            if e.status == 404:
                return None
            self.logger.error(f"VirtualService 조회 실패: {name} - {e.reason}")
            raise VirtualServiceReadException(
                name=name, namespace=namespace, reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )
        except Exception as e:
            raise VirtualServiceReadException(name=name, namespace=namespace, reason=str(e))

    async def patch_virtualservice(
        self,
        name: str,
        namespace: str,
        hosts: List[str],
        label_patch: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """VirtualService의 hosts와 레이블을 부분 업데이트(patch)."""
        patch_body: Dict[str, Any] = {"spec": {"hosts": hosts}}
        if label_patch:
            patch_body["metadata"] = {"labels": label_patch}

        try:
            result = await self.k8s_client.custom_objects.patch_namespaced_custom_object(
                group=ISTIO_VS_GROUP,
                version=ISTIO_VS_VERSION,
                namespace=namespace,
                plural=ISTIO_VS_PLURAL,
                name=name,
                body=patch_body,
                content_type="application/merge-patch+json",
            )
            self.logger.info(f"VirtualService patch 완료: {name} (namespace: {namespace})")
            return result
        except ApiException as e:
            self.logger.error(f"VirtualService patch 실패: {name} - {e.reason}")
            raise VirtualServiceCreationException(
                name=name, namespace=namespace, reason=e.reason or str(e),
                detail={"status": e.status},
            )

    async def find_by_label(self, label_selector: str) -> Optional[Dict[str, Any]]:
        """label_selector로 클러스터 전체에서 VirtualService 1건 조회.

        예) label_selector="madp.io/dns-id=123"
        """
        try:
            result = await self.k8s_client.custom_objects.list_cluster_custom_object(
                group=ISTIO_VS_GROUP,
                version=ISTIO_VS_VERSION,
                plural=ISTIO_VS_PLURAL,
                label_selector=label_selector,
            )
            items = result.get("items", [])
            return items[0] if items else None
        except ApiException as e:
            self.logger.error(f"VirtualService label 조회 실패: {label_selector} - {e.reason}")
            raise VirtualServiceReadException(
                name="(label-search)", namespace="*", reason=e.reason or str(e),
                detail={"status": e.status},
            )
        except Exception as e:
            raise VirtualServiceReadException(name="(label-search)", namespace="*", reason=str(e))

    async def delete_virtualservice(self, name: str, namespace: str) -> bool:
        """VirtualService 삭제. 없으면 성공으로 처리 (멱등성)."""
        self.logger.info(f"VirtualService 삭제 시도: {name} (namespace: {namespace})")

        existing = await self.get_virtualservice(name, namespace)
        if not existing:
            self.logger.info(f"VirtualService 없음 (이미 삭제됨): {name} (namespace: {namespace})")
            return True

        try:
            await self.k8s_client.custom_objects.delete_namespaced_custom_object(
                group=ISTIO_VS_GROUP,
                version=ISTIO_VS_VERSION,
                namespace=namespace,
                plural=ISTIO_VS_PLURAL,
                name=name,
            )
            self.logger.info(f"VirtualService 삭제 완료: {name} (namespace: {namespace})")
            return True

        except ApiException as e:
            if e.status == 404:
                return True
            self.logger.error(f"VirtualService 삭제 실패: {name} - {e.reason}")
            raise VirtualServiceDeletionException(
                name=name, namespace=namespace, reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            raise VirtualServiceDeletionException(name=name, namespace=namespace, reason=str(e))
