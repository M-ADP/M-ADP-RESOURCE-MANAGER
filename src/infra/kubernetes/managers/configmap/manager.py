"""ConfigMap 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1ConfigMap,
    V1ObjectMeta,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    ConfigMapCreationException,
    ConfigMapReadException,
    ConfigMapUpdateException,
    ConfigMapDeletionException,
    ConfigMapListException,
)


class ConfigMapManager:
    """ConfigMap 리소스를 관리하는 클래스
    """

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_configmap(
        self,
        name: str,
        namespace: str,
        data: Optional[Dict[str, str]] = None,
        binary_data: Optional[Dict[str, bytes]] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> V1ConfigMap:
        """ConfigMap 비동기 생성

        Args:
            name: ConfigMap 이름
            namespace: 네임스페이스
            data: 문자열 데이터 딕셔너리
            binary_data: 바이너리 데이터 딕셔너리
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리

        Returns:
            생성되거나 기존에 존재하는 V1ConfigMap 객체

        Raises:
            ConfigMapCreationException: ConfigMap 생성 실패 시
        """
        self.logger.info(
            f"ConfigMap 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_configmap(name, namespace)
        if existing:
            self.logger.info(
                f"ConfigMap 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # ConfigMap 객체 생성
        configmap = V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {},
                annotations=annotations or {},
            ),
            data=data or {},
            binary_data=binary_data,
        )

        try:
            cm = await self.k8s_client.core_v1.create_namespaced_config_map(
                namespace=namespace,
                body=configmap,
            )
            self.logger.info(
                f"ConfigMap 생성 완료: {name} (namespace: {namespace})"
            )
            return cm

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"ConfigMap 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_configmap(name, namespace)
                if existing:
                    return existing

            self.logger.logger.error(
                f"ConfigMap 생성 실패: {name} - {e.reason}"
            )
            raise ConfigMapCreationException(
                configmap_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ConfigMap 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise ConfigMapCreationException(
                configmap_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_configmap(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1ConfigMap]:
        """ConfigMap 비동기 조회

        Args:
            name: ConfigMap 이름
            namespace: 네임스페이스

        Returns:
            V1ConfigMap 객체 또는 None (존재하지 않으면)

        Raises:
            ConfigMapReadException: 조회 실패 시 (404 제외)
        """
        try:
            cm = await self.k8s_client.core_v1.read_namespaced_config_map(
                name=name,
                namespace=namespace,
            )
            return cm

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"ConfigMap 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise ConfigMapReadException(
                configmap_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ConfigMap 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise ConfigMapReadException(
                configmap_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_configmap(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """ConfigMap 비동기 삭제

        Args:
            name: ConfigMap 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            ConfigMapDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"ConfigMap 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_configmap(name, namespace)
        if not existing:
            self.logger.warning(
                f"ConfigMap가 존재하지 않음: {name} (namespace: {namespace})"
            )
            raise ConfigMapDeletionException(
                configmap_name=name,
                namespace=namespace,
                reason="ConfigMap does not exist",
            )

        try:
            await self.k8s_client.core_v1.delete_namespaced_config_map(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(
                f"ConfigMap 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(
                    f"ConfigMap 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.logger.error(
                f"ConfigMap 삭제 실패: {name} - {e.reason}"
            )
            raise ConfigMapDeletionException(
                configmap_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ConfigMap 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise ConfigMapDeletionException(
                configmap_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_configmaps(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1ConfigMap]:
        """ConfigMap 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1ConfigMap 객체 리스트

        Raises:
            ConfigMapListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.core_v1.list_namespaced_config_map(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.core_v1.list_config_map_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.logger.error(
                f"ConfigMap 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise ConfigMapListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ConfigMap 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise ConfigMapListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """ConfigMap 존재 여부 확인

        Args:
            name: ConfigMap 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        cm = await self.get_configmap(name, namespace)
        return cm is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1ConfigMap:
        """ConfigMap 레이블 업데이트

        Args:
            name: ConfigMap 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1ConfigMap 객체

        Raises:
            ConfigMapUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"ConfigMap 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_configmap(name, namespace)
        if not existing:
            raise ConfigMapUpdateException(
                configmap_name=name,
                namespace=namespace,
                reason="ConfigMap does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            cm = await self.k8s_client.core_v1.patch_namespaced_config_map(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"ConfigMap 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return cm

        except ApiException as e:
            self.logger.logger.error(
                f"ConfigMap 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise ConfigMapUpdateException(
                configmap_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ConfigMap 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ConfigMapUpdateException(
                configmap_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_data(
        self,
        name: str,
        namespace: str,
        data: Dict[str, str],
        merge: bool = True,
    ) -> V1ConfigMap:
        """ConfigMap 데이터 업데이트

        Args:
            name: ConfigMap 이름
            namespace: 네임스페이스
            data: 새로운 데이터 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1ConfigMap 객체

        Raises:
            ConfigMapUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"ConfigMap 데이터 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_configmap(name, namespace)
        if not existing:
            raise ConfigMapUpdateException(
                configmap_name=name,
                namespace=namespace,
                reason="ConfigMap does not exist",
            )

        # 병합 또는 교체
        if merge and existing.data:
            new_data = {**existing.data, **data}
        else:
            new_data = data

        # Patch 요청
        body = {"data": new_data}

        try:
            cm = await self.k8s_client.core_v1.patch_namespaced_config_map(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"ConfigMap 데이터 업데이트 완료: {name} (namespace: {namespace})"
            )
            return cm

        except ApiException as e:
            self.logger.logger.error(
                f"ConfigMap 데이터 업데이트 실패: {name} - {e.reason}"
            )
            raise ConfigMapUpdateException(
                configmap_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"ConfigMap 데이터 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ConfigMapUpdateException(
                configmap_name=name,
                namespace=namespace,
                reason=str(e),
            )
