"""VaultClient 유닛 테스트"""

import pytest
from unittest.mock import MagicMock, patch
import hvac
from hvac.exceptions import VaultError, InvalidPath

from src.infra import VaultClient
from src.infra.vault.exceptions import (
    VaultSecretException,
)
from src.core import Logger


@pytest.fixture
def mock_logger():
    """Mock Logger 픽스처"""
    logger = MagicMock(spec=Logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_hvac_client():
    """Mock hvac.Client 픽스처"""
    client = MagicMock(spec=hvac.Client)

    # Kubernetes Auth Mock
    client.auth.kubernetes = MagicMock()
    client.auth.kubernetes.create_role = MagicMock()
    client.auth.kubernetes.read_role = MagicMock()
    client.auth.kubernetes.delete_role = MagicMock()
    client.auth.kubernetes.list_roles = MagicMock()

    # System (Policy) Mock
    client.sys = MagicMock()
    client.sys.create_or_update_policy = MagicMock()
    client.sys.read_policy = MagicMock()
    client.sys.delete_policy = MagicMock()
    client.sys.list_policies = MagicMock()
    client.sys.read_health_status = MagicMock()

    # Secrets KV v2 Mock
    client.secrets.kv.v2 = MagicMock()
    client.secrets.kv.v2.create_or_update_secret = MagicMock()
    client.secrets.kv.v2.read_secret_version = MagicMock()
    client.secrets.kv.v2.delete_metadata_and_all_versions = MagicMock()
    client.secrets.kv.v2.list_secrets = MagicMock()

    return client


@pytest.fixture
def vault_client(mock_hvac_client, mock_logger):
    """VaultClient 픽스처"""
    with patch("infra.vault.client.hvac.Client", return_value=mock_hvac_client):
        client = VaultClient(
            vault_addr="http://vault.default.svc.cluster.local:8200",
            vault_token="test-token",
            logger=mock_logger,
        )
        # Replace the real client with our mock
        client.client = mock_hvac_client
        return client


class TestVaultClientInit:
    """VaultClient 초기화 테스트"""

    def test_init_with_token(self, mock_logger):
        """토큰으로 초기화 테스트"""
        with patch("infra.vault.client.hvac.Client") as mock_client_class:
            client = VaultClient(
                vault_addr="http://vault.example.com:8200",
                vault_token="test-token",
                logger=mock_logger,
            )

            assert client.vault_addr == "http://vault.example.com:8200"
            assert client.vault_token == "test-token"
            assert client.logger == mock_logger

            mock_client_class.assert_called_once_with(
                url="http://vault.example.com:8200",
                token="test-token",
                namespace=None,
            )

    def test_init_without_logger(self):
        """로거 없이 초기화 테스트"""
        with patch("infra.vault.client.hvac.Client"):
            client = VaultClient(
                vault_addr="http://vault.example.com:8200",
                vault_token="test-token",
            )
            assert client.logger is not None  # 기본 Logger 생성됨


class TestSecretManagement:
    """Secret 관리 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_create_secret_success(self, vault_client, mock_hvac_client):
        """Secret 생성 성공 테스트"""
        mock_hvac_client.secrets.kv.v2.create_or_update_secret.return_value = {
            "request_id": "abc-123",
            "data": {"version": 1}
        }

        result = await vault_client.create_secret(
            path="myapp/db",
            secret={"username": "admin", "password": "secret123"},
        )

        assert result == {"request_id": "abc-123", "data": {"version": 1}}
        # _run_in_executor를 통해 호출되므로 직접 호출은 확인 불가
        # 대신 로그 호출 확인
        vault_client.logger.info.assert_any_call("Vault Secret 생성: secret/data/myapp/db")
        vault_client.logger.info.assert_any_call("Vault Secret 생성 완료: secret/data/myapp/db")

    @pytest.mark.asyncio
    async def test_create_secret_vault_error(self, vault_client, mock_hvac_client):
        """Secret 생성 실패 테스트 (VaultError)"""
        async def mock_executor(func, *args, **kwargs):
            raise VaultError("Permission denied")

        vault_client._run_in_executor = mock_executor

        with pytest.raises(VaultSecretException) as exc_info:
            await vault_client.create_secret(
                path="myapp/db",
                secret={"password": "secret123"},
            )

        assert "Secret" in str(exc_info.value)
        assert "생성 실패" in str(exc_info.value)
        assert "secret/data/myapp/db" in str(exc_info.value)
        vault_client.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_secret_success(self, vault_client, mock_hvac_client):
        """Secret 조회 성공 테스트"""
        mock_hvac_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "username": "admin",
                    "password": "secret123"
                },
                "metadata": {"version": 1}
            }
        }

        result = await vault_client.get_secret("myapp/db")

        assert result == {"username": "admin", "password": "secret123"}

    @pytest.mark.asyncio
    async def test_get_secret_not_found(self, vault_client, mock_hvac_client):
        """Secret 조회 실패 테스트 (존재하지 않음)"""
        async def mock_executor(func, *args, **kwargs):
            raise InvalidPath("Secret not found")

        vault_client._run_in_executor = mock_executor

        result = await vault_client.get_secret("myapp/nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_secret_with_version(self, vault_client, mock_hvac_client):
        """특정 버전 Secret 조회 테스트"""
        mock_hvac_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {"password": "old-password"},
                "metadata": {"version": 1}
            }
        }

        result = await vault_client.get_secret("myapp/db", version=1)

        assert result == {"password": "old-password"}

    @pytest.mark.asyncio
    async def test_delete_secret_success(self, vault_client, mock_hvac_client):
        """Secret 삭제 성공 테스트"""
        mock_hvac_client.secrets.kv.v2.delete_metadata_and_all_versions.return_value = None

        result = await vault_client.delete_secret("myapp/db")

        assert result is True
        vault_client.logger.info.assert_any_call("Vault Secret 삭제: secret/data/myapp/db")
        vault_client.logger.info.assert_any_call("Vault Secret 삭제 완료: secret/data/myapp/db")

    @pytest.mark.asyncio
    async def test_delete_secret_not_found(self, vault_client, mock_hvac_client):
        """존재하지 않는 Secret 삭제 테스트 (멱등성)"""
        async def mock_executor(func, *args, **kwargs):
            raise InvalidPath("Secret not found")

        vault_client._run_in_executor = mock_executor

        result = await vault_client.delete_secret("myapp/nonexistent")

        assert result is True
        vault_client.logger.info.assert_any_call("Vault Secret이 이미 없음: secret/data/myapp/nonexistent")

    @pytest.mark.asyncio
    async def test_delete_secret_vault_error(self, vault_client, mock_hvac_client):
        """Secret 삭제 실패 테스트 (VaultError)"""
        async def mock_executor(func, *args, **kwargs):
            raise VaultError("Permission denied")

        vault_client._run_in_executor = mock_executor

        with pytest.raises(VaultSecretException) as exc_info:
            await vault_client.delete_secret("myapp/db")

        assert "Secret" in str(exc_info.value)
        assert "삭제 실패" in str(exc_info.value)
        assert "secret/data/myapp/db" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_secrets_success(self, vault_client, mock_hvac_client):
        """Secret 목록 조회 성공 테스트"""
        mock_hvac_client.secrets.kv.v2.list_secrets.return_value = {
            "data": {
                "keys": ["db", "api-key", "jwt-secret"]
            }
        }

        result = await vault_client.list_secrets("myapp/")

        assert result == ["db", "api-key", "jwt-secret"]

    @pytest.mark.asyncio
    async def test_list_secrets_empty(self, vault_client, mock_hvac_client):
        """빈 디렉토리 Secret 목록 조회 테스트"""
        async def mock_executor(func, *args, **kwargs):
            raise InvalidPath("No secrets found")

        vault_client._run_in_executor = mock_executor

        result = await vault_client.list_secrets("empty/")

        assert result == []

    @pytest.mark.asyncio
    async def test_list_secrets_root(self, vault_client, mock_hvac_client):
        """루트 경로 Secret 목록 조회 테스트"""
        mock_hvac_client.secrets.kv.v2.list_secrets.return_value = {
            "data": {
                "keys": ["myapp/", "shared/", "config/"]
            }
        }

        result = await vault_client.list_secrets("")

        assert result == ["myapp/", "shared/", "config/"]


class TestKubernetesRoleManagement:
    """Kubernetes Auth Role 관리 테스트"""

    @pytest.mark.asyncio
    async def test_create_kubernetes_role_success(self, vault_client, mock_hvac_client):
        """Kubernetes Role 생성 성공 테스트"""
        mock_hvac_client.auth.kubernetes.create_role.return_value = {}

        result = await vault_client.create_kubernetes_role(
            role_name="test-role",
            bound_service_account_names=["test-sa"],
            bound_service_account_namespaces=["default"],
            policies=["test-policy"],
        )

        assert result == {}
        vault_client.logger.info.assert_any_call("Vault Kubernetes Role 생성: test-role")

    @pytest.mark.asyncio
    async def test_get_kubernetes_role_success(self, vault_client, mock_hvac_client):
        """Kubernetes Role 조회 성공 테스트"""
        mock_hvac_client.auth.kubernetes.read_role.return_value = {
            "data": {
                "bound_service_account_names": ["test-sa"],
                "policies": ["test-policy"]
            }
        }

        result = await vault_client.get_kubernetes_role("test-role")

        assert result == {
            "bound_service_account_names": ["test-sa"],
            "policies": ["test-policy"]
        }

    @pytest.mark.asyncio
    async def test_get_kubernetes_role_not_found(self, vault_client, mock_hvac_client):
        """존재하지 않는 Kubernetes Role 조회 테스트"""
        async def mock_executor(func, *args, **kwargs):
            raise InvalidPath("Role not found")

        vault_client._run_in_executor = mock_executor

        result = await vault_client.get_kubernetes_role("nonexistent")

        assert result is None


class TestPolicyManagement:
    """Policy 관리 테스트"""

    @pytest.mark.asyncio
    async def test_create_policy_success(self, vault_client, mock_hvac_client):
        """Policy 생성 성공 테스트"""
        mock_hvac_client.sys.create_or_update_policy.return_value = None

        policy_hcl = 'path "secret/data/myapp/*" {\n  capabilities = ["read"]\n}'

        result = await vault_client.create_policy("test-policy", policy_hcl)

        assert result is True
        vault_client.logger.info.assert_any_call("Vault Policy 생성: test-policy")

    @pytest.mark.asyncio
    async def test_get_policy_success(self, vault_client, mock_hvac_client):
        """Policy 조회 성공 테스트"""
        policy_hcl = 'path "secret/data/myapp/*" {\n  capabilities = ["read"]\n}'
        mock_hvac_client.sys.read_policy.return_value = {
            "data": {"policy": policy_hcl}
        }

        result = await vault_client.get_policy("test-policy")

        assert result == policy_hcl

    @pytest.mark.asyncio
    async def test_generate_policy_hcl(self):
        """Policy HCL 생성 헬퍼 테스트"""
        policy_hcl = VaultClient.generate_policy_hcl(
            secret_paths=["secret/data/myapp/db", "secret/data/myapp/api-key"],
            capabilities=["read"],
        )

        assert 'path "secret/data/myapp/db"' in policy_hcl
        assert 'path "secret/data/myapp/api-key"' in policy_hcl
        assert 'capabilities = ["read"]' in policy_hcl


class TestHealthCheck:
    """Health Check 테스트"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, vault_client, mock_hvac_client):
        """Health Check 성공 테스트"""
        mock_hvac_client.sys.read_health_status.return_value = {
            "initialized": True,
            "sealed": False
        }

        result = await vault_client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, vault_client, mock_hvac_client):
        """Health Check 실패 테스트"""
        async def mock_executor(func, *args, **kwargs):
            raise Exception("Connection refused")

        vault_client._run_in_executor = mock_executor

        result = await vault_client.health_check()

        assert result is False
