"""Istio Gateway 리소스 관리 클래스"""

from typing import Any, Dict, List, Optional

from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    GatewayCreationException,
    GatewayReadException,
    GatewayDeletionException,
    GatewayListException,
)


# Istio Gateway CRD 정보
ISTIO_GATEWAY_GROUP = "networking.istio.io"
ISTIO_GATEWAY_VERSION = "v1beta1"
ISTIO_GATEWAY_PLURAL = "gateways"


class IstioGatewayManager:
    """Istio Gateway 리소스를 관리하는 클래스

    Istio Gateway는 Custom Resource이므로 CustomObjectsApi를 사용합니다.
    """

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_gateway(
        self,
        name: str,
        namespace: str,
        servers: List[Dict[str, Any]],
        selector: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Istio Gateway 비동기 생성

        Args:
            name: Gateway 이름
            namespace: 네임스페이스
            servers: Gateway 서버 설정 리스트
            selector: 인그레스 게이트웨이 파드 셀렉터
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리

        Returns:
            생성된 Gateway 객체 (dict)

        Raises:
            GatewayCreationException: Gateway 생성 실패 시
        """
        self.logger.info(
            f"Gateway 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_gateway(name, namespace)
        if existing:
            self.logger.info(
                f"Gateway 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # Gateway 객체 생성
        gateway_body = {
            "apiVersion": f"{ISTIO_GATEWAY_GROUP}/{ISTIO_GATEWAY_VERSION}",
            "kind": "Gateway",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": labels or {},
                "annotations": annotations or {},
            },
            "spec": {
                "selector": selector or {"istio": "ingressgateway"},
                "servers": servers,
            },
        }

        try:
            gateway = await self.k8s_client.custom_objects.create_namespaced_custom_object(
                group=ISTIO_GATEWAY_GROUP,
                version=ISTIO_GATEWAY_VERSION,
                namespace=namespace,
                plural=ISTIO_GATEWAY_PLURAL,
                body=gateway_body,
            )
            self.logger.info(
                f"Gateway 생성 완료: {name} (namespace: {namespace})"
            )
            return gateway

        except ApiException as e:
            if e.status == 409:
                self.logger.warning(
                    f"Gateway 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_gateway(name, namespace)
                if existing:
                    return existing

            self.logger.error(
                f"Gateway 생성 실패: {name} - {e.reason}"
            )
            raise GatewayCreationException(
                gateway_name=name,
                namespace=namespace,
                reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Gateway 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise GatewayCreationException(
                gateway_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_gateway(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, Any]]:
        """Gateway 비동기 조회

        Args:
            name: Gateway 이름
            namespace: 네임스페이스

        Returns:
            Gateway 객체 (dict) 또는 None

        Raises:
            GatewayReadException: 조회 실패 시 (404 제외)
        """
        try:
            gateway = await self.k8s_client.custom_objects.get_namespaced_custom_object(
                group=ISTIO_GATEWAY_GROUP,
                version=ISTIO_GATEWAY_VERSION,
                namespace=namespace,
                plural=ISTIO_GATEWAY_PLURAL,
                name=name,
            )
            return gateway

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.error(
                f"Gateway 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise GatewayReadException(
                gateway_name=name,
                namespace=namespace,
                reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Gateway 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise GatewayReadException(
                gateway_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_gateway(
        self,
        name: str,
        namespace: str,
    ) -> bool:
        """Gateway 비동기 삭제

        Args:
            name: Gateway 이름
            namespace: 네임스페이스

        Returns:
            삭제 성공 여부

        Raises:
            GatewayDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"Gateway 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_gateway(name, namespace)
        if not existing:
            self.logger.warning(
                f"Gateway가 존재하지 않음: {name} (namespace: {namespace})"
            )
            return True  # 멱등성 보장

        try:
            await self.k8s_client.custom_objects.delete_namespaced_custom_object(
                group=ISTIO_GATEWAY_GROUP,
                version=ISTIO_GATEWAY_VERSION,
                namespace=namespace,
                plural=ISTIO_GATEWAY_PLURAL,
                name=name,
            )
            self.logger.info(
                f"Gateway 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            if e.status == 404:
                self.logger.warning(
                    f"Gateway 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.error(
                f"Gateway 삭제 실패: {name} - {e.reason}"
            )
            raise GatewayDeletionException(
                gateway_name=name,
                namespace=namespace,
                reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Gateway 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise GatewayDeletionException(
                gateway_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_gateways(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Gateway 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터

        Returns:
            Gateway 객체 리스트

        Raises:
            GatewayListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.custom_objects.list_namespaced_custom_object(
                    group=ISTIO_GATEWAY_GROUP,
                    version=ISTIO_GATEWAY_VERSION,
                    namespace=namespace,
                    plural=ISTIO_GATEWAY_PLURAL,
                    label_selector=label_selector,
                )
            else:
                result = await self.k8s_client.custom_objects.list_cluster_custom_object(
                    group=ISTIO_GATEWAY_GROUP,
                    version=ISTIO_GATEWAY_VERSION,
                    plural=ISTIO_GATEWAY_PLURAL,
                    label_selector=label_selector,
                )

            return result.get("items", [])

        except ApiException as e:
            self.logger.error(
                f"Gateway 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise GatewayListException(
                namespace=namespace,
                reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Gateway 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise GatewayListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """Gateway 존재 여부 확인

        Args:
            name: Gateway 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        gateway = await self.get_gateway(name, namespace)
        return gateway is not None
