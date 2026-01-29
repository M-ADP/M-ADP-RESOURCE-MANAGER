"""KubernetesClientImpl 유닛 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.dependencies.kubernetes import get_kubernetes_client
from src.core.logger import Logger
from src.infra.kubernetes.client import KubernetesClientImpl
from src.common.config.kubernetes import KubernetesConfig


@pytest.fixture
def mock_logger():
    """Mock Logger 픽스처"""
    logger = MagicMock(spec=Logger)
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.logger = MagicMock()
    return logger


@pytest.fixture
def k8s_config():
    """KubernetesConfig 픽스처"""
    config = MagicMock(spec=KubernetesConfig)
    config.use_in_cluster_config = False
    config.kubeconfig_path = None
    config.api_server_url = None
    config.default_namespace = "default"
    return config


@pytest.fixture
def k8s_client(k8s_config, mock_logger):
    """KubernetesClientImpl 픽스처"""
    return KubernetesClientImpl(k8s_config, mock_logger)


class TestKubernetesClient:
    """KubernetesClientImpl 테스트 클래스"""

    def test_init(self, k8s_client, k8s_config, mock_logger):
        """초기화 테스트"""
        assert k8s_client.config == k8s_config
        assert k8s_client.logger == mock_logger
        assert k8s_client.api_client is None
        assert k8s_client.core_v1 is None
        assert k8s_client.apps_v1 is None
        assert k8s_client.rbac_v1 is None
        assert k8s_client.batch_v1 is None

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.config.load_kube_config', new_callable=AsyncMock)
    async def test_load_config_default(self, mock_load_kube_config, k8s_client):
        """기본 kubeconfig 로드 테스트"""
        await k8s_client._load_config()

        mock_load_kube_config.assert_called_once_with()
        k8s_client.logger.info.assert_any_call("기본 Kubernetes 설정 로드 중")
        k8s_client.logger.info.assert_any_call("Kubernetes 설정 로드 완료")

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.config.load_kube_config', new_callable=AsyncMock)
    async def test_load_config_with_path(self, mock_load_kube_config, k8s_client):
        """특정 kubeconfig 경로로 로드 테스트"""
        k8s_client.config.kubeconfig_path = "/path/to/kubeconfig"

        await k8s_client._load_config()

        mock_load_kube_config.assert_called_once_with(config_file="/path/to/kubeconfig")
        k8s_client.logger.info.assert_any_call("Kubernetes 설정 파일 로드 중: /path/to/kubeconfig")

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.config.load_incluster_config')
    async def test_load_config_in_cluster(self, mock_load_incluster_config, k8s_client):
        """클러스터 내부 설정 로드 테스트"""
        k8s_client.config.use_in_cluster_config = True

        await k8s_client._load_config()

        mock_load_incluster_config.assert_called_once_with()
        k8s_client.logger.info.assert_any_call("클러스터 내부 Kubernetes 설정 로드 중")

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.config.load_kube_config', new_callable=AsyncMock)
    async def test_load_config_failure(self, mock_load_kube_config, k8s_client):
        """설정 로드 실패 테스트"""
        mock_load_kube_config.side_effect = Exception("Config load failed")

        with pytest.raises(Exception, match="Config load failed"):
            await k8s_client._load_config()

        k8s_client.logger.logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.client.ApiClient')
    @patch('infra.kubernetes.client.CoreV1Api')
    @patch('infra.kubernetes.client.AppsV1Api')
    @patch('infra.kubernetes.client.RbacAuthorizationV1Api')
    @patch('infra.kubernetes.client.BatchV1Api')
    async def test_initialize_clients(
        self,
        mock_batch_v1,
        mock_rbac_v1,
        mock_apps_v1,
        mock_core_v1,
        mock_api_client,
        k8s_client
    ):
        """API 클라이언트 초기화 테스트"""
        mock_api_client_instance = MagicMock()
        mock_api_client.return_value = mock_api_client_instance

        await k8s_client._initialize_clients()

        # ApiClient 생성 확인
        mock_api_client.assert_called_once()
        assert k8s_client.api_client == mock_api_client_instance

        # 각 API 클라이언트 생성 확인
        mock_core_v1.assert_called_once_with(mock_api_client_instance)
        mock_apps_v1.assert_called_once_with(mock_api_client_instance)
        mock_rbac_v1.assert_called_once_with(mock_api_client_instance)
        mock_batch_v1.assert_called_once_with(mock_api_client_instance)

        k8s_client.logger.info.assert_called_with("Kubernetes API 클라이언트 초기화 완료")

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.client.ApiClient')
    async def test_initialize_clients_with_custom_host(self, mock_api_client, k8s_client):
        """커스텀 API 서버 URL 설정 테스트"""
        k8s_client.config.api_server_url = "https://custom-k8s-api.example.com"
        mock_api_client_instance = MagicMock()
        mock_api_client_instance.configuration = MagicMock()
        mock_api_client.return_value = mock_api_client_instance

        await k8s_client._initialize_clients()

        assert mock_api_client_instance.configuration.host == "https://custom-k8s-api.example.com"

    @pytest.mark.asyncio
    async def test_close(self, k8s_client):
        """리소스 정리 테스트"""
        mock_api_client = AsyncMock()
        k8s_client.api_client = mock_api_client

        await k8s_client.close()

        mock_api_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_client(self, k8s_client):
        """API 클라이언트 없이 close 호출 테스트"""
        k8s_client.api_client = None

        # 예외 발생 없이 정상 종료되어야 함
        await k8s_client.close()

    def test_default_namespace(self, k8s_client):
        """기본 네임스페이스 반환 테스트"""
        assert k8s_client.default_namespace == "default"

        k8s_client.config.default_namespace = "custom-namespace"
        assert k8s_client.default_namespace == "custom-namespace"

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.config.load_kube_config', new_callable=AsyncMock)
    @patch('infra.kubernetes.client.client.ApiClient')
    async def test_initialize(self, mock_api_client, mock_load_kube_config, k8s_client):
        """전체 초기화 테스트"""
        mock_api_client_instance = MagicMock()
        mock_api_client.return_value = mock_api_client_instance

        await k8s_client.initialize()

        # config와 clients가 모두 초기화되었는지 확인
        mock_load_kube_config.assert_called_once()
        mock_api_client.assert_called_once()
        assert k8s_client.api_client is not None

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.config.load_kube_config', new_callable=AsyncMock)
    @patch('infra.kubernetes.client.client.ApiClient')
    async def test_context_manager(self, mock_api_client, mock_load_kube_config, k8s_client):
        """비동기 컨텍스트 매니저 테스트"""
        mock_api_client_instance = AsyncMock()
        mock_api_client.return_value = mock_api_client_instance

        async with k8s_client as client:
            assert client == k8s_client
            assert k8s_client.api_client is not None

        # close가 호출되었는지 확인
        mock_api_client_instance.close.assert_called_once()


class TestGetKubernetesClient:
    """get_kubernetes_client 함수 테스트"""

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.config.load_kube_config', new_callable=AsyncMock)
    @patch('infra.kubernetes.client.client.ApiClient')
    async def test_get_kubernetes_client_singleton(self, mock_api_client, mock_load_kube_config):
        """싱글톤 패턴 테스트"""
        # 싱글톤 초기화
        import src.infra.kubernetes.client as client_module
        client_module._k8s_client_instance = None

        mock_api_client_instance = AsyncMock()
        mock_api_client.return_value = mock_api_client_instance

        # 첫 번째 호출
        client1 = await get_kubernetes_client()

        # 두 번째 호출
        client2 = await get_kubernetes_client()

        # 같은 인스턴스여야 함
        assert client1 is client2

        # initialize는 한 번만 호출되어야 함
        assert mock_load_kube_config.call_count == 1

        # 정리
        client_module._k8s_client_instance = None

    @pytest.mark.asyncio
    @patch('infra.kubernetes.client.config.load_kube_config', new_callable=AsyncMock)
    @patch('infra.kubernetes.client.client.ApiClient')
    @patch('core.logger.get_logger')
    async def test_get_kubernetes_client_with_custom_config(
        self,
        mock_get_logger,
        mock_api_client,
        mock_load_kube_config
    ):
        """커스텀 설정으로 클라이언트 생성 테스트"""
        # 싱글톤 초기화
        import src.infra.kubernetes.client as client_module
        client_module._k8s_client_instance = None

        custom_config = MagicMock(spec=KubernetesConfig)
        custom_config.use_in_cluster_config = False
        custom_config.kubeconfig_path = None
        custom_config.api_server_url = None
        custom_config.default_namespace = "custom"

        custom_logger = MagicMock(spec=Logger)

        mock_api_client_instance = AsyncMock()
        mock_api_client.return_value = mock_api_client_instance

        client = await get_kubernetes_client(k8s_config=custom_config, logger=custom_logger)

        assert client.config == custom_config
        assert client.logger == custom_logger

        # 기본값으로 생성하는 함수가 호출되지 않아야 함
        mock_get_logger.assert_not_called()

        # 정리
        client_module._k8s_client_instance = None
