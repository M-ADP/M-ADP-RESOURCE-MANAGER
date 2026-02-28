"""StorageClass 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1StorageClass,
    V1ObjectMeta,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    StorageClassCreationException,
    StorageClassReadException,
    StorageClassDeletionException,
)


class StorageClassManager:
    """StorageClass 리소스를 관리하는 클래스"""

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_storage_class(
        self,
        name: str,
        provisioner: str,
        parameters: Dict[str, str],
        reclaim_policy: str = "Delete",
        allow_volume_expansion: bool = True,
        volume_binding_mode: str = "Immediate",
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> V1StorageClass:
        """StorageClass 비동기 생성

        Args:
            name: StorageClass 이름
            provisioner: 프로비저너 이름
            parameters: 프로비저너 파라미터
            reclaim_policy: 회수 정책 (Delete, Retain)
            allow_volume_expansion: 볼륨 확장 허용 여부
            volume_binding_mode: 볼륨 바인딩 모드 (Immediate, WaitForFirstConsumer)
            labels: 레이블
            annotations: 어노테이션

        Returns:
            생성된 V1StorageClass 객체
        """
        self.logger.info(f"StorageClass 생성 시도: {name}")

        existing = await self.get_storage_class(name)
        if existing:
            self.logger.info(f"StorageClass 이미 존재함: {name}")
            return existing

        sc = V1StorageClass(
            api_version="storage.k8s.io/v1",
            kind="StorageClass",
            metadata=V1ObjectMeta(
                name=name,
                labels=labels or {},
                annotations=annotations or {},
            ),
            provisioner=provisioner,
            parameters=parameters,
            reclaim_policy=reclaim_policy,
            allow_volume_expansion=allow_volume_expansion,
            volume_binding_mode=volume_binding_mode,
        )

        try:
            result = await self.k8s_client.storage_v1.create_storage_class(body=sc)
            self.logger.info(f"StorageClass 생성 완료: {name}")
            return result
        except ApiException as e:
            if e.status == 409:
                existing = await self.get_storage_class(name)
                if existing:
                    return existing
            self.logger.logger.error(f"StorageClass 생성 실패: {name} - {e.reason}")
            raise StorageClassCreationException(
                sc_name=name,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

    async def get_storage_class(self, name: str) -> Optional[V1StorageClass]:
        """StorageClass 조회

        Args:
            name: StorageClass 이름

        Returns:
            V1StorageClass 객체 또는 None
        """
        try:
            return await self.k8s_client.storage_v1.read_storage_class(name=name)
        except ApiException as e:
            if e.status == 404:
                return None
            raise StorageClassReadException(sc_name=name, reason=e.reason)

    async def delete_storage_class(self, name: str) -> bool:
        """StorageClass 삭제

        Args:
            name: StorageClass 이름

        Returns:
            삭제 성공 여부
        """
        try:
            await self.k8s_client.storage_v1.delete_storage_class(name=name)
            return True
        except ApiException as e:
            if e.status == 404:
                return True
            raise StorageClassDeletionException(sc_name=name, reason=e.reason)

    async def ensure_linstor_storage_classes(
        self,
        storage_pool: str = "fast",
    ):
        """Linstor StorageClass 생성 보장

        Args:
            storage_pool: Linstor 스토리지 풀 이름
        """

        await self.create_storage_class(
            name="linstor-pv-fast",
            provisioner="linstor.csi.linbit.com",
            parameters={
                "linstor.csi.linbit.com/storagePool": storage_pool,
            },
            reclaim_policy="Delete",
            allow_volume_expansion=True,
            volume_binding_mode="WaitForFirstConsumer"
        )
