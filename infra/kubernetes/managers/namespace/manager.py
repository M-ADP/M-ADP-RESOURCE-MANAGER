from typing import Optional, Dict, List
from kubernetes.client import V1Namespace, V1ObjectMeta, V1NamespaceList
from kubernetes.client.rest import ApiException

from infra.kubernetes.client import KubernetesClient
from .exceptions import (
    NamespaceCreationException,
    NamespaceNotFoundException,
    NamespaceDeletionException,
    NamespaceUpdateException,
    NamespaceReadException,
    NamespaceListException,
)
from core.logger import Logger


class NamespaceManager:
    """
    Kubernetes Namespace 리소스 관리 클래스
    Namespace의 생성, 조회, 삭제 등의 작업을 담당한다.
    """

    def __init__(self, k8s_client: KubernetesClient, logger: Optional[Logger] = None):
        """
        NamespaceManager 초기화
        
        Args:
            k8s_client: Kubernetes API 클라이언트
            logger: 로거 인스턴스 (선택적)
        """
        self.k8s_client = k8s_client
        self.logger = logger or Logger()

    def create_namespace(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> V1Namespace:
        """
        Namespace 생성 (멱등성 보장)
        이미 존재하는 경우 기존 Namespace를 반환한다.
        
        Args:
            name: Namespace 이름
            labels: Namespace에 적용할 레이블
            annotations: Namespace에 적용할 어노테이션
            
        Returns:
            V1Namespace: 생성되거나 기존에 존재하는 Namespace 객체
            
        Raises:
            NamespaceCreationException: Namespace 생성 실패 시
        """
        try:
            # 이미 존재하는지 확인 (멱등성)
            existing = self.get_namespace(name)
            if existing:
                self.logger.info(f"Namespace '{name}'이(가) 이미 존재합니다. 기존 리소스를 반환합니다.")
                return existing

            # Namespace 객체 생성
            namespace = V1Namespace(
                api_version="v1",
                kind="Namespace",
                metadata=V1ObjectMeta(
                    name=name,
                    labels=labels or {},
                    annotations=annotations or {}
                )
            )

            # Namespace 생성
            self.logger.info(f"Namespace '{name}' 생성 중...")
            created_namespace = self.k8s_client.core_v1.create_namespace(body=namespace)
            self.logger.info(f"Namespace '{name}' 생성 완료")

            return created_namespace

        except ApiException as e:
            if e.status == 409:  # Conflict - 이미 존재
                self.logger.info(f"Namespace '{name}'이(가) 이미 존재합니다. (409 Conflict)")
                return self.get_namespace(name)
            else:
                self.logger.error(f"Namespace '{name}' 생성 실패: {e.reason}", exc_info=True)
                raise NamespaceCreationException(
                    namespace_name=name,
                    reason=e.reason or "알 수 없는 오류",
                    detail={"api_status_code": e.status}
                )
        except (NamespaceNotFoundException, NamespaceCreationException, NamespaceReadException):
            # 커스텀 예외는 그대로 전파
            raise
        except Exception as e:
            self.logger.error(f"Namespace '{name}' 생성 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
            raise NamespaceCreationException(
                namespace_name=name,
                reason=str(e)
            )

    def get_namespace(self, name: str) -> Optional[V1Namespace]:
        """
        Namespace 조회
        
        Args:
            name: Namespace 이름
            
        Returns:
            V1Namespace: Namespace 객체, 존재하지 않으면 None
            
        Raises:
            NamespaceReadException: Namespace 조회 실패 시 (404 제외)
        """
        try:
            namespace = self.k8s_client.core_v1.read_namespace(name=name)
            return namespace
        except ApiException as e:
            if e.status == 404:
                return None
            else:
                self.logger.error(f"Namespace '{name}' 조회 실패: {e.reason}", exc_info=True)
                raise NamespaceReadException(
                    namespace_name=name,
                    reason=e.reason or "알 수 없는 오류",
                    api_status_code=e.status
                )
        except NamespaceReadException:
            # 커스텀 예외는 그대로 전파
            raise
        except Exception as e:
            self.logger.error(f"Namespace '{name}' 조회 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
            raise NamespaceReadException(
                namespace_name=name,
                reason=str(e),
                api_status_code=500
            )

    def delete_namespace(self, name: str, grace_period_seconds: int = 30) -> bool:
        """
        Namespace 삭제
        
        Args:
            name: Namespace 이름
            grace_period_seconds: 종료 유예 시간 (초)
            
        Returns:
            bool: 삭제 성공 여부
            
        Raises:
            NamespaceDeletionException: Namespace 삭제 실패 시
        """
        try:
            # Namespace 존재 여부 확인
            if not self.exists(name):
                self.logger.info(f"Namespace '{name}'이(가) 존재하지 않습니다. 삭제 작업을 건너뜁니다.")
                return True

            self.logger.info(f"Namespace '{name}' 삭제 중...")
            self.k8s_client.core_v1.delete_namespace(
                name=name,
                grace_period_seconds=grace_period_seconds
            )
            self.logger.info(f"Namespace '{name}' 삭제 요청 완료")
            return True

        except ApiException as e:
            if e.status == 404:
                self.logger.info(f"Namespace '{name}'이(가) 이미 삭제되었습니다.")
                return True
            else:
                self.logger.error(f"Namespace '{name}' 삭제 실패: {e.reason}", exc_info=True)
                raise NamespaceDeletionException(
                    namespace_name=name,
                    reason=e.reason or "알 수 없는 오류",
                    detail={"api_status_code": e.status}
                )
        except NamespaceDeletionException:
            # 커스텀 예외는 그대로 전파
            raise
        except Exception as e:
            self.logger.error(f"Namespace '{name}' 삭제 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
            raise NamespaceDeletionException(
                namespace_name=name,
                reason=str(e)
            )

    def list_namespaces(
        self,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None
    ) -> List[V1Namespace]:
        """
        Namespace 목록 조회
        
        Args:
            label_selector: 레이블 셀렉터 (예: "env=production,team=backend")
            field_selector: 필드 셀렉터 (예: "metadata.name=default")
            
        Returns:
            List[V1Namespace]: Namespace 목록
            
        Raises:
            NamespaceListException: Namespace 목록 조회 실패 시
        """
        try:
            namespace_list: V1NamespaceList = self.k8s_client.core_v1.list_namespace(
                label_selector=label_selector,
                field_selector=field_selector
            )
            return namespace_list.items

        except ApiException as e:
            self.logger.error(f"Namespace 목록 조회 실패: {e.reason}", exc_info=True)
            raise NamespaceListException(
                reason=e.reason or "알 수 없는 오류",
                api_status_code=e.status
            )
        except NamespaceListException:
            # 커스텀 예외는 그대로 전파
            raise
        except Exception as e:
            self.logger.error(f"Namespace 목록 조회 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
            raise NamespaceListException(
                reason=str(e),
                api_status_code=500
            )

    def exists(self, name: str) -> bool:
        """
        Namespace 존재 여부 확인
        
        Args:
            name: Namespace 이름
            
        Returns:
            bool: 존재 여부
        """
        return self.get_namespace(name) is not None

    def update_labels(
        self,
        name: str,
        labels: Dict[str, str],
        merge: bool = True
    ) -> V1Namespace:
        """
        Namespace 레이블 업데이트
        
        Args:
            name: Namespace 이름
            labels: 업데이트할 레이블
            merge: True인 경우 기존 레이블과 병합, False인 경우 완전 대체
            
        Returns:
            V1Namespace: 업데이트된 Namespace 객체
            
        Raises:
            NamespaceNotFoundException: Namespace가 존재하지 않을 때
            NamespaceUpdateException: Namespace 업데이트 실패 시
        """
        try:
            # 기존 Namespace 조회
            namespace = self.get_namespace(name)
            if not namespace:
                raise NamespaceNotFoundException(
                    namespace_name=name
                )

            # 레이블 업데이트
            if merge and namespace.metadata.labels:
                updated_labels = {**namespace.metadata.labels, **labels}
            else:
                updated_labels = labels

            namespace.metadata.labels = updated_labels

            # Namespace 패치
            self.logger.info(f"Namespace '{name}' 레이블 업데이트 중...")
            updated_namespace = self.k8s_client.core_v1.patch_namespace(
                name=name,
                body=namespace
            )
            self.logger.info(f"Namespace '{name}' 레이블 업데이트 완료")

            return updated_namespace

        except ApiException as e:
            self.logger.error(f"Namespace '{name}' 레이블 업데이트 실패: {e.reason}", exc_info=True)
            raise NamespaceUpdateException(
                namespace_name=name,
                reason=e.reason or "알 수 없는 오류",
                detail={"api_status_code": e.status}
            )
        except (NamespaceNotFoundException, NamespaceUpdateException, NamespaceReadException):
            # 커스텀 예외는 그대로 전파
            raise
        except Exception as e:
            self.logger.error(f"Namespace '{name}' 레이블 업데이트 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
            raise NamespaceUpdateException(
                namespace_name=name,
                reason=str(e)
            )

    def get_namespace_status(self, name: str) -> Optional[str]:
        """
        Namespace 상태 조회
        
        Args:
            name: Namespace 이름
            
        Returns:
            Optional[str]: Namespace 상태 (Active, Terminating 등), 존재하지 않으면 None
        """
        namespace = self.get_namespace(name)
        if namespace and namespace.status:
            return namespace.status.phase
        return None
