"""VPA 리소스 관리 클래스"""
from typing import Optional, Dict, List, Any
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger

# VPA CRD 정보
VPA_GROUP = "autoscaling.k8s.io"
VPA_VERSION = "v1"
VPA_PLURAL = "verticalpodautoscalers"


class VpaManager:
    """VPA CRD 리소스를 관리하는 클래스"""

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_vpa(self, namespace: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """VPA 비동기 생성"""
        name = body.get("metadata", {}).get("name")
        self.logger.info(f"VPA 생성 시도: {name} (namespace: {namespace})")
        
        try:
            # 멱등성: 이미 존재하면 조회하여 반환
            existing_vpa = await self.get_vpa(name, namespace)
            if existing_vpa:
                self.logger.info(f"VPA 이미 존재함: {name}. 기존 리소스 반환.")
                return existing_vpa

            vpa = await self.k8s_client.custom_objects.create_namespaced_custom_object(
                group=VPA_GROUP,
                version=VPA_VERSION,
                namespace=namespace,
                plural=VPA_PLURAL,
                body=body,
            )
            self.logger.info(f"VPA 생성 완료: {name}")
            return vpa
        except ApiException as e:
            if e.status == 409: # 이미 존재
                return await self.get_vpa(name, namespace)
            self.logger.error(f"VPA 생성 실패: {name} - {e.reason}")
            raise
        except Exception as e:
            self.logger.error(f"VPA 생성 중 예외 발생: {name} - {str(e)}")
            raise

    async def get_vpa(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        """VPA 비동기 조회"""
        try:
            return await self.k8s_client.custom_objects.get_namespaced_custom_object(
                group=VPA_GROUP,
                version=VPA_VERSION,
                namespace=namespace,
                plural=VPA_PLURAL,
                name=name,
            )
        except ApiException as e:
            if e.status == 404:
                return None
            self.logger.error(f"VPA 조회 실패: {name} - {e.reason}")
            raise

    async def list_vpas(self, namespace: str) -> List[Dict[str, Any]]:
        """네임스페이스의 모든 VPA 목록 비동기 조회"""
        try:
            result = await self.k8s_client.custom_objects.list_namespaced_custom_object(
                group=VPA_GROUP,
                version=VPA_VERSION,
                namespace=namespace,
                plural=VPA_PLURAL,
            )
            return result.get("items", [])
        except ApiException as e:
            self.logger.error(f"VPA 목록 조회 실패 (namespace: {namespace}) - {e.reason}")
            raise

    async def delete_vpa(self, name: str, namespace: str) -> bool:
        """VPA 비동기 삭제"""
        self.logger.info(f"VPA 삭제 시도: {name} (namespace: {namespace})")
        try:
            await self.k8s_client.custom_objects.delete_namespaced_custom_object(
                group=VPA_GROUP,
                version=VPA_VERSION,
                namespace=namespace,
                plural=VPA_PLURAL,
                name=name,
            )
            self.logger.info(f"VPA 삭제 완료: {name}")
            return True
        except ApiException as e:
            if e.status == 404:
                self.logger.info(f"VPA 이미 삭제됨: {name}")
                return True
            self.logger.error(f"VPA 삭제 실패: {name} - {e.reason}")
            raise
        except Exception as e:
            self.logger.error(f"VPA 삭제 중 예외 발생: {name} - {str(e)}")
            raise
