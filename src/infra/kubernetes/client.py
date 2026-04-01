from kubernetes_asyncio import client, config
from kubernetes_asyncio.client import (
    CoreV1Api,
    AppsV1Api,
    RbacAuthorizationV1Api,
    BatchV1Api,
    AutoscalingV2Api,
    StorageV1Api,
    CustomObjectsApi,
)

from src.core.kubernetes.kubernetes_client import KubernetesClient


class KubernetesClientImpl(KubernetesClient):
    """Kubernetes API 비동기 클라이언트 래퍼"""

    async def initialize(self) -> None:
        await self._load_config()
        await self._initialize_clients()

    async def _load_config(self) -> None:
        """Kubernetes 설정 비동기 로드"""
        try:
            if self.config.use_in_cluster_config:
                # Pod 내부에서 실행 중인 경우
                self.logger.info("클러스터 내부 Kubernetes 설정 로드 중")
                config.load_incluster_config()
            elif self.config.kubeconfig_path:
                # 특정 kubeconfig 파일 사용
                self.logger.info(
                    f"Kubernetes 설정 파일 로드 중: {self.config.kubeconfig_path}"
                )
                await config.load_kube_config(config_file=self.config.kubeconfig_path)
            else:
                # in-cluster 자동 감지 후 기본 kubeconfig 폴백
                try:
                    config.load_incluster_config()
                    self.logger.info("클러스터 내부 Kubernetes 설정 자동 감지 완료")
                except Exception:
                    self.logger.info("기본 Kubernetes 설정 로드 중")
                    await config.load_kube_config()

            self.logger.info("Kubernetes 설정 로드 완료")

        except Exception as e:
            self.logger.logger.error(f"Kubernetes 설정 로드 실패: {e}", exc_info=True)
            raise

    async def _initialize_clients(self) -> None:
        """Kubernetes API 클라이언트 비동기 초기화"""
        # API 클라이언트 생성
        self.api_client = client.ApiClient()

        if self.config.api_server_url:
            self.api_client.configuration.host = self.config.api_server_url

        # 각종 API 클라이언트 생성
        self.core_v1 = CoreV1Api(self.api_client)
        self.apps_v1 = AppsV1Api(self.api_client)
        self.rbac_v1 = RbacAuthorizationV1Api(self.api_client)
        self.batch_v1 = BatchV1Api(self.api_client)
        self.autoscaling_v2 = AutoscalingV2Api(self.api_client)
        self.storage_v1 = StorageV1Api(self.api_client)
        self.custom_objects = CustomObjectsApi(self.api_client)

        self.logger.info("Kubernetes API 클라이언트 초기화 완료")

    async def close(self) -> None:
        """API 클라이언트 리소스 정리"""
        if self.api_client:
            await self.api_client.close()

    @property
    def default_namespace(self) -> str:
        """기본 네임스페이스 반환"""
        return self.config.default_namespace

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()
