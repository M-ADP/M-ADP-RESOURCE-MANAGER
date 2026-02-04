"""PersistentVolumeClaim 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1PersistentVolumeClaim,
    V1ObjectMeta,
    V1PersistentVolumeClaimSpec,
    V1ResourceRequirements,
    V1LabelSelector,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    PersistentVolumeClaimCreationException,
    PersistentVolumeClaimReadException,
    PersistentVolumeClaimUpdateException,
    PersistentVolumeClaimDeletionException,
    PersistentVolumeClaimListException,
)


class PersistentVolumeClaimManager:
    """PersistentVolumeClaim 리소스를 관리하는 클래스
    """

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_pvc(
        self,
        name: str,
        namespace: str,
        storage_size: str,
        access_modes: Optional[List[str]] = None,
        storage_class_name: Optional[str] = None,
        volume_mode: Optional[str] = None,
        selector: Optional[V1LabelSelector] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> V1PersistentVolumeClaim:
        """PersistentVolumeClaim 비동기 생성

        Args:
            name: PVC 이름
            namespace: 네임스페이스
            storage_size: 스토리지 크기 (예: "10Gi", "500Mi")
            access_modes: 접근 모드 리스트 (기본값: ["ReadWriteOnce"])
            storage_class_name: 스토리지 클래스 이름
            volume_mode: 볼륨 모드 (Filesystem 또는 Block)
            selector: PV 선택을 위한 레이블 셀렉터
            labels: PVC 레이블
            annotations: PVC 어노테이션

        Returns:
            생성되거나 기존에 존재하는 V1PersistentVolumeClaim 객체

        Raises:
            PersistentVolumeClaimCreationException: PVC 생성 실패 시
        """
        self.logger.info(
            f"PVC 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_pvc(name, namespace)
        if existing:
            self.logger.info(
                f"PVC 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # 기본값 설정
        pvc_labels = labels or {"app_deployment": name}
        pvc_access_modes = access_modes or ["ReadWriteOnce"]

        # PVC 객체 생성
        pvc = V1PersistentVolumeClaim(
            api_version="v1",
            kind="PersistentVolumeClaim",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=pvc_labels,
                annotations=annotations or {},
            ),
            spec=V1PersistentVolumeClaimSpec(
                access_modes=pvc_access_modes,
                resources=V1ResourceRequirements(
                    requests={"storage": storage_size}
                ),
                storage_class_name=storage_class_name,
                volume_mode=volume_mode,
                selector=selector,
            ),
        )

        try:
            p = await self.k8s_client.core_v1.create_namespaced_persistent_volume_claim(
                namespace=namespace,
                body=pvc,
            )
            self.logger.info(
                f"PVC 생성 완료: {name} (namespace: {namespace})"
            )
            return p

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"PVC 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_pvc(name, namespace)
                if existing:
                    return existing

            self.logger.logger.error(
                f"PVC 생성 실패: {name} - {e.reason}"
            )
            raise PersistentVolumeClaimCreationException(
                pvc_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"PVC 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise PersistentVolumeClaimCreationException(
                pvc_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_pvc(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1PersistentVolumeClaim]:
        """PersistentVolumeClaim 비동기 조회

        Args:
            name: PVC 이름
            namespace: 네임스페이스

        Returns:
            V1PersistentVolumeClaim 객체 또는 None (존재하지 않으면)

        Raises:
            PersistentVolumeClaimReadException: 조회 실패 시 (404 제외)
        """
        try:
            p = await self.k8s_client.core_v1.read_namespaced_persistent_volume_claim(
                name=name,
                namespace=namespace,
            )
            return p

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"PVC 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise PersistentVolumeClaimReadException(
                pvc_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"PVC 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise PersistentVolumeClaimReadException(
                pvc_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_pvc(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """PersistentVolumeClaim 비동기 삭제

        Args:
            name: PVC 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            PersistentVolumeClaimDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"PVC 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_pvc(name, namespace)
        if not existing:
            self.logger.warning(
                f"PVC가 존재하지 않음: {name} (namespace: {namespace})"
            )
            raise PersistentVolumeClaimDeletionException(
                pvc_name=name,
                namespace=namespace,
                reason="PersistentVolumeClaim does not exist",
            )

        try:
            await self.k8s_client.core_v1.delete_namespaced_persistent_volume_claim(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(
                f"PVC 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(
                    f"PVC 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.logger.error(
                f"PVC 삭제 실패: {name} - {e.reason}"
            )
            raise PersistentVolumeClaimDeletionException(
                pvc_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"PVC 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise PersistentVolumeClaimDeletionException(
                pvc_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_pvcs(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1PersistentVolumeClaim]:
        """PersistentVolumeClaim 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app_deployment=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1PersistentVolumeClaim 객체 리스트

        Raises:
            PersistentVolumeClaimListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.core_v1.list_namespaced_persistent_volume_claim(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.core_v1.list_persistent_volume_claim_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.logger.error(
                f"PVC 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise PersistentVolumeClaimListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"PVC 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise PersistentVolumeClaimListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """PersistentVolumeClaim 존재 여부 확인

        Args:
            name: PVC 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        p = await self.get_pvc(name, namespace)
        return p is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1PersistentVolumeClaim:
        """PersistentVolumeClaim 레이블 업데이트

        Args:
            name: PVC 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1PersistentVolumeClaim 객체

        Raises:
            PersistentVolumeClaimUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"PVC 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_pvc(name, namespace)
        if not existing:
            raise PersistentVolumeClaimUpdateException(
                pvc_name=name,
                namespace=namespace,
                reason="PersistentVolumeClaim does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            p = await self.k8s_client.core_v1.patch_namespaced_persistent_volume_claim(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"PVC 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return p

        except ApiException as e:
            self.logger.logger.error(
                f"PVC 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise PersistentVolumeClaimUpdateException(
                pvc_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"PVC 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise PersistentVolumeClaimUpdateException(
                pvc_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def resize_pvc(
        self,
        name: str,
        namespace: str,
        new_storage_size: str,
    ) -> V1PersistentVolumeClaim:
        """PersistentVolumeClaim 스토리지 크기 변경

        Args:
            name: PVC 이름
            namespace: 네임스페이스
            new_storage_size: 새로운 스토리지 크기 (예: "20Gi")

        Returns:
            업데이트된 V1PersistentVolumeClaim 객체

        Raises:
            PersistentVolumeClaimUpdateException: 업데이트 실패 시

        Note:
            스토리지 크기는 증가만 가능하며, StorageClass가 볼륨 확장을 지원해야 함
        """
        self.logger.info(
            f"PVC 크기 변경: {name} (namespace: {namespace}, new_size: {new_storage_size})"
        )

        # 존재 여부 확인
        existing = await self.get_pvc(name, namespace)
        if not existing:
            raise PersistentVolumeClaimUpdateException(
                pvc_name=name,
                namespace=namespace,
                reason="PersistentVolumeClaim does not exist",
            )

        # Patch 요청
        body = {
            "spec": {
                "resources": {
                    "requests": {
                        "storage": new_storage_size
                    }
                }
            }
        }

        try:
            p = await self.k8s_client.core_v1.patch_namespaced_persistent_volume_claim(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"PVC 크기 변경 완료: {name} (namespace: {namespace})"
            )
            return p

        except ApiException as e:
            self.logger.logger.error(
                f"PVC 크기 변경 실패: {name} - {e.reason}"
            )
            raise PersistentVolumeClaimUpdateException(
                pvc_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"PVC 크기 변경 중 예외 발생: {name} - {str(e)}"
            )
            raise PersistentVolumeClaimUpdateException(
                pvc_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_pvc_status(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, any]]:
        """PersistentVolumeClaim 상태 조회

        Args:
            name: PVC 이름
            namespace: 네임스페이스

        Returns:
            PVC 상태 정보 딕셔너리 또는 None

        Raises:
            PersistentVolumeClaimReadException: 조회 실패 시
        """
        pvc = await self.get_pvc(name, namespace)
        if not pvc or not pvc.status:
            return None

        status = pvc.status
        return {
            "phase": status.phase,
            "access_modes": status.access_modes,
            "capacity": status.capacity,
            "conditions": [
                {
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message,
                    "last_probe_time": condition.last_probe_time,
                    "last_transition_time": condition.last_transition_time,
                }
                for condition in (status.conditions or [])
            ],
        }

    async def is_bound(self, name: str, namespace: str) -> bool:
        """PVC가 PV에 바인딩되었는지 확인

        Args:
            name: PVC 이름
            namespace: 네임스페이스

        Returns:
            바인딩 여부
        """
        status = await self.get_pvc_status(name, namespace)
        if not status:
            return False

        return status.get("phase") == "Bound"
