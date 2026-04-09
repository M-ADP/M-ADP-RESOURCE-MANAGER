"""AppDeployment 도메인 Repository 인터페이스"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.core.kubernetes.configmap import ConfigMap
from src.core.kubernetes.deployment import Deployment
from src.core.kubernetes.hpa import HorizontalPodAutoscaler
from src.core.kubernetes.persistent_volume_claim import PersistentVolumeClaim
from src.core.kubernetes.pod import Event, Pod, PodLogs
from src.core.kubernetes.service_account import ServiceAccount


class AppDeploymentRepository(ABC):
    """
    AppDeployment 도메인 Repository.

    App Deployment 생명주기에 필요한 모든 인프라 연산을 도메인 동사(verb)로 표현한다.
    호출자는 Kubernetes나 Vault의 세부사항을 알 필요가 없다.
    """

    # ── Deployment ──────────────────────────────────────────────────────────

    @abstractmethod
    async def deploy(self, deployment: Deployment) -> Deployment:
        """Deployment 배포 (생성 또는 업데이트, 멱등성 보장)"""

    @abstractmethod
    async def find_deployment(self, name: str, namespace: str) -> Optional[Deployment]:
        """이름으로 Deployment 조회"""

    @abstractmethod
    async def undeploy(self, deployment: Deployment) -> bool:
        """Deployment 및 연관 리소스 제거"""

    @abstractmethod
    async def scale(self, deployment: Deployment, replicas: int) -> Deployment:
        """Deployment 레플리카 수 조정"""

    @abstractmethod
    async def resize_container(
        self,
        deployment: Deployment,
        container_name: str,
        requests: Optional[Dict[str, str]] = None,
        limits: Optional[Dict[str, str]] = None,
    ) -> Deployment:
        """Deployment 컨테이너 CPU/메모리 리소스 조정"""

    # ── Storage (PVC) ────────────────────────────────────────────────────────

    @abstractmethod
    async def provision_storage(
        self, pvc: PersistentVolumeClaim
    ) -> PersistentVolumeClaim:
        """스토리지 프로비저닝 (PVC 생성, 멱등성 보장)"""

    @abstractmethod
    async def find_storage(
        self, name: str, namespace: str
    ) -> Optional[PersistentVolumeClaim]:
        """이름으로 스토리지(PVC) 조회"""

    @abstractmethod
    async def deprovision_storage(self, name: str, namespace: str) -> bool:
        """스토리지 해제 (PVC 삭제)"""

    @abstractmethod
    async def expand_storage(
        self, pvc: PersistentVolumeClaim, new_size: str
    ) -> PersistentVolumeClaim:
        """스토리지 용량 확장 (축소 불가)"""

    # ── Identity (ServiceAccount) ────────────────────────────────────────────

    @abstractmethod
    async def bind_identity(self, service_account: ServiceAccount) -> ServiceAccount:
        """Deployment에 ID(ServiceAccount) 바인딩"""

    @abstractmethod
    async def unbind_identity(self, name: str, namespace: str) -> bool:
        """Deployment ID(ServiceAccount) 바인딩 해제"""

    # ── Autoscale (HPA) ──────────────────────────────────────────────────────

    @abstractmethod
    async def enable_autoscale(
        self, hpa: HorizontalPodAutoscaler
    ) -> HorizontalPodAutoscaler:
        """오토스케일 활성화 (HPA 생성 또는 업데이트, 멱등성 보장)"""

    @abstractmethod
    async def disable_autoscale(self, deployment: Deployment) -> bool:
        """오토스케일 비활성화 (HPA 삭제, deployment.hpa_name 자동 활용)"""

    # ── Observation (Pod) ────────────────────────────────────────────────────

    @abstractmethod
    async def get_pods(self, deployment: Deployment) -> List[Pod]:
        """Deployment 소속 Pod 목록 조회"""

    @abstractmethod
    async def get_pod_logs(
        self,
        pod_name: str,
        namespace: str,
        tail_lines: Optional[int] = None,
        since_seconds: Optional[int] = None,
        timestamps: bool = False,
    ) -> Optional[PodLogs]:
        """Pod 로그 조회"""

    @abstractmethod
    async def get_events(self, deployment: Deployment) -> List[Event]:
        """Deployment 관련 이벤트 조회"""

    # ── Environment (ConfigMap) ──────────────────────────────────────────────

    @abstractmethod
    async def set_env(
        self,
        deployment: Deployment,
        data: Dict[str, str],
        labels: Optional[Dict[str, str]] = None,
    ) -> ConfigMap:
        """환경변수 설정 (없으면 생성, 있으면 병합, deployment.env_configmap_name 자동 활용)"""

    @abstractmethod
    async def replace_env(
        self, deployment: Deployment, data: Dict[str, str]
    ) -> ConfigMap:
        """환경변수 완전 교체 (기존 키 모두 제거 후 새 데이터로 대체)"""

    @abstractmethod
    async def get_env(self, deployment: Deployment) -> Optional[ConfigMap]:
        """환경변수 ConfigMap 조회 (deployment.env_configmap_name 자동 활용)"""

    @abstractmethod
    async def clear_env(self, deployment: Deployment) -> bool:
        """환경변수 ConfigMap 삭제"""

    # ── Secret (Vault) ───────────────────────────────────────────────────────

    @property
    @abstractmethod
    def secret_mount_point(self) -> str:
        """Vault KV Secret Engine 마운트 포인트"""

    @abstractmethod
    async def store_secret(
        self,
        deployment: Deployment,
        data: Dict,
    ) -> str:
        """
        Vault Secret 저장 및 접근 구조 설정.

        Secret 이름은 deployment.vault_secret_name으로 자동 결정된다.

        내부적으로:
        - Vault KV에 secret 저장
        - Vault Policy 생성 (이미 있으면 유지)
        - Kubernetes Auth Role 생성/업데이트
        - Deployment에 Vault Agent Injector annotation 주입

        반환값: 저장된 secret의 전체 경로 (mount_point/data/...)
        """

    @abstractmethod
    async def list_app_secrets(self, deployment: Deployment) -> List[str]:
        """Deployment에 등록된 Secret 목록 조회"""

    @abstractmethod
    async def revoke_secret(self, deployment: Deployment) -> bool:
        """
        Secret 삭제 및 접근 구조 전체 정리.

        내부적으로:
        - Vault KV에서 secret 삭제
        - Policy + Role 자동 정리

        반환값: 정리 성공 여부
        """
