from typing import Optional
from kubernetes import client, config
from kubernetes.client import CoreV1Api, AppsV1Api, RbacAuthorizationV1Api, BatchV1Api

from core.config.kubernetes import KubernetesConfig
from core.logger import Logger


class KubernetesClient:
    """Kubernetes API 클라이언트 래퍼"""

    def __init__(self, k8s_config: KubernetesConfig, logger: Logger):
        self.config = k8s_config
        self.logger = logger
        self._load_config()
        self._initialize_clients()

    def _load_config(self) -> None:
        try:
            if self.config.use_in_cluster_config:
                # Pod 내부에서 실행 중인 경우
                self.logger.info("클러스터 내부 Kubernetes 설정 로드 중")
                config.load_incluster_config()
            elif self.config.kubeconfig_path:
                # 특정 kubeconfig 파일 사용
                self.logger.info(f"Kubernetes 설정 파일 로드 중: {self.config.kubeconfig_path}")
                config.load_kube_config(config_file=self.config.kubeconfig_path)
            else:
                # 기본 kubeconfig 사용 (~/.kube/config)
                self.logger.info("기본 Kubernetes 설정 로드 중")
                config.load_kube_config()

            self.logger.info("Kubernetes 설정 로드 완료")

        except Exception as e:
            self.logger.logger.error(f"Kubernetes 설정 로드 실패: {e}", exc_info=True)
            raise

    def _initialize_clients(self) -> None:
        """Kubernetes API 클라이언트 초기화"""
        # API 설정
        configuration = client.Configuration.get_default_copy()

        if self.config.api_server_url:
            configuration.host = self.config.api_server_url

        # 각종 API 클라이언트 생성
        self.core_v1 = CoreV1Api(client.ApiClient(configuration))
        self.apps_v1 = AppsV1Api(client.ApiClient(configuration))
        self.rbac_v1 = RbacAuthorizationV1Api(client.ApiClient(configuration))
        self.batch_v1 = BatchV1Api(client.ApiClient(configuration))

        self.logger.info("Kubernetes API 클라이언트 초기화 완료")

    @property
    def default_namespace(self) -> str:
        """기본 네임스페이스 반환"""
        return self.config.default_namespace


# 싱글톤 패턴으로 전역 클라이언트 인스턴스 관리
_k8s_client_instance: Optional[KubernetesClient] = None


def get_kubernetes_client(
    k8s_config: Optional[KubernetesConfig] = None,
    logger: Optional[Logger] = None
) -> KubernetesClient:
    """Kubernetes 클라이언트 인스턴스 반환 (의존성 주입용)"""
    global _k8s_client_instance

    if _k8s_client_instance is None:
        from core.config.kubernetes import KubernetesConfig
        from core.logger import get_logger

        config = k8s_config or KubernetesConfig()
        log = logger or get_logger()
        _k8s_client_instance = KubernetesClient(config, log)

    return _k8s_client_instance
