"""SecretManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1ServiceAccount,
    V1ObjectMeta,
    V1Deployment,
    V1StatefulSet,
)

from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra import VaultClient
from src.infra.kubernetes.managers.secret import (
    SecretManager,
    SecretAccessBindingException,
    VaultInjectionException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClientImpl Mock 픽스처"""
    client = MagicMock(spec=KubernetesClientImpl)
    client.core_v1 = AsyncMock()
    client.apps_v1 = AsyncMock()
    return client


@pytest.fixture
def vault_client():
    """VaultClient Mock 픽스처"""
    client = MagicMock(spec=VaultClient)
    client.create_kubernetes_role = AsyncMock(return_value={})
    client.get_kubernetes_role = AsyncMock(return_value=None)
    client.delete_kubernetes_role = AsyncMock(return_value=True)
    client.list_kubernetes_roles = AsyncMock(return_value=[])
    client.create_policy = AsyncMock(return_value=True)
    client.get_policy = AsyncMock(return_value=None)
    client.delete_policy = AsyncMock(return_value=True)
    client.list_policies = AsyncMock(return_value=[])
    client.generate_policy_hcl = MagicMock(return_value="path \"secret/data/*\" { capabilities = [\"read\"] }")
    return client


@pytest.fixture
def secret_manager(k8s_client, vault_client):
    """SecretManager 픽스처"""
    return SecretManager(k8s_client, vault_client)


@pytest.fixture
def mock_service_account():
    """Mock V1ServiceAccount 객체"""
    return V1ServiceAccount(
        api_version="v1",
        kind="ServiceAccount",
        metadata=V1ObjectMeta(
            name="test-sa",
            namespace="test-ns",
            annotations={
                "vault.hashicorp.com/role": "test-vault-role",
            },
        ),
    )


class TestSecretManagerInit:
    """SecretManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client, vault_client):
        """정상 초기화 테스트"""
        manager = SecretManager(k8s_client, vault_client)
        assert manager.k8s_client == k8s_client
        assert manager.vault_client == vault_client
        assert manager.logger is not None


class TestVaultRoleManagement:
    """Vault Role 관리 테스트"""

    @pytest.mark.asyncio
    async def test_create_vault_role(self, secret_manager, vault_client):
        """Vault Role 생성 테스트"""
        result = await secret_manager.create_vault_role(
            role_name="test-role",
            bound_service_account_names=["test-sa"],
            bound_service_account_namespaces=["test-ns"],
            policies=["test-policy"],
        )

        assert result == {}
        vault_client.create_kubernetes_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_vault_role(self, secret_manager, vault_client):
        """Vault Role 조회 테스트"""
        vault_client.get_kubernetes_role.return_value = {"role": "data"}
        
        result = await secret_manager.get_vault_role("test-role")

        assert result == {"role": "data"}
        vault_client.get_kubernetes_role.assert_called_once_with("test-role")

    @pytest.mark.asyncio
    async def test_delete_vault_role(self, secret_manager, vault_client):
        """Vault Role 삭제 테스트"""
        result = await secret_manager.delete_vault_role("test-role")

        assert result is True
        vault_client.delete_kubernetes_role.assert_called_once_with("test-role")

    @pytest.mark.asyncio
    async def test_list_vault_roles(self, secret_manager, vault_client):
        """Vault Role 목록 조회 테스트"""
        vault_client.list_kubernetes_roles.return_value = ["role1", "role2"]
        
        result = await secret_manager.list_vault_roles()

        assert result == ["role1", "role2"]
        vault_client.list_kubernetes_roles.assert_called_once()


class TestVaultPolicyManagement:
    """Vault Policy 관리 테스트"""

    @pytest.mark.asyncio
    async def test_create_vault_policy(self, secret_manager, vault_client):
        """Vault Policy 생성 테스트"""
        result = await secret_manager.create_vault_policy(
            policy_name="test-policy",
            secret_paths=["secret/data/app/db"],
        )

        assert result is True
        vault_client.generate_policy_hcl.assert_called_once()
        vault_client.create_policy.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_vault_policy(self, secret_manager, vault_client):
        """Vault Policy 조회 테스트"""
        vault_client.get_policy.return_value = "policy hcl"
        
        result = await secret_manager.get_vault_policy("test-policy")

        assert result == "policy hcl"
        vault_client.get_policy.assert_called_once_with("test-policy")

    @pytest.mark.asyncio
    async def test_delete_vault_policy(self, secret_manager, vault_client):
        """Vault Policy 삭제 테스트"""
        result = await secret_manager.delete_vault_policy("test-policy")

        assert result is True
        vault_client.delete_policy.assert_called_once_with("test-policy")

    @pytest.mark.asyncio
    async def test_list_vault_policies(self, secret_manager, vault_client):
        """Vault Policy 목록 조회 테스트"""
        vault_client.list_policies.return_value = ["policy1", "policy2"]
        
        result = await secret_manager.list_vault_policies()

        assert result == ["policy1", "policy2"]
        vault_client.list_policies.assert_called_once()


class TestServiceAccountBinding:
    """ServiceAccount Vault 바인딩 테스트"""

    @pytest.mark.asyncio
    async def test_bind_serviceaccount_to_vault(
        self, secret_manager, k8s_client, vault_client
    ):
        """ServiceAccount Vault 바인딩 테스트"""
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock()

        result = await secret_manager.bind_serviceaccount_to_vault(
            service_account_name="test-sa",
            namespace="test-ns",
            vault_role_name="test-vault-role",
            secret_paths=["secret/data/app/db"],
        )

        assert result["vault_role"] == "test-vault-role"
        assert result["vault_policy"] == "test-ns-test-sa-policy"
        assert result["service_account"] == "test-ns/test-sa"
        
        vault_client.create_policy.assert_called_once()
        vault_client.create_kubernetes_role.assert_called_once()
        k8s_client.core_v1.patch_namespaced_service_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_bind_serviceaccount_to_vault_failure(
        self, secret_manager, vault_client
    ):
        """ServiceAccount Vault 바인딩 실패 테스트"""
        vault_client.create_policy.side_effect = Exception("Vault error")

        with pytest.raises(SecretAccessBindingException) as exc_info:
            await secret_manager.bind_serviceaccount_to_vault(
                service_account_name="test-sa",
                namespace="test-ns",
                vault_role_name="test-vault-role",
                secret_paths=["secret/data/app/db"],
            )

        assert "Vault error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unbind_serviceaccount_from_vault(
        self, secret_manager, k8s_client, vault_client, mock_service_account
    ):
        """ServiceAccount Vault 바인딩 해제 테스트"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock()

        result = await secret_manager.unbind_serviceaccount_from_vault(
            service_account_name="test-sa",
            namespace="test-ns",
        )

        assert result is True
        vault_client.delete_kubernetes_role.assert_called_once_with("test-vault-role")
        vault_client.delete_policy.assert_called_once()

    @pytest.mark.asyncio
    async def test_unbind_serviceaccount_no_binding(
        self, secret_manager, k8s_client
    ):
        """바인딩 없는 ServiceAccount 바인딩 해제 테스트"""
        sa_without_binding = V1ServiceAccount(
            metadata=V1ObjectMeta(
                name="test-sa",
                namespace="test-ns",
                annotations={},
            ),
        )
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=sa_without_binding
        )

        result = await secret_manager.unbind_serviceaccount_from_vault(
            service_account_name="test-sa",
            namespace="test-ns",
        )

        assert result is True


class TestVaultInjection:
    """Vault 설정 주입 테스트"""

    @pytest.mark.asyncio
    async def test_inject_vault_agent_to_deployment(
        self, secret_manager, k8s_client
    ):
        """Deployment에 Vault Agent 주입 테스트"""
        mock_deployment = V1Deployment(
            metadata=V1ObjectMeta(name="test-deployment", namespace="test-ns")
        )
        k8s_client.apps_v1.patch_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )

        result = await secret_manager.inject_vault_agent_to_deployment(
            deployment_name="test-deployment",
            namespace="test-ns",
            vault_role="test-vault-role",
            secret_configs=[
                {"name": "db-creds", "path": "secret/data/app/db"},
            ],
        )

        assert result == mock_deployment
        k8s_client.apps_v1.patch_namespaced_deployment.assert_called_once()

    @pytest.mark.asyncio
    async def test_inject_vault_agent_to_statefulset(
        self, secret_manager, k8s_client
    ):
        """StatefulSet에 Vault Agent 주입 테스트"""
        mock_statefulset = V1StatefulSet(
            metadata=V1ObjectMeta(name="test-sts", namespace="test-ns")
        )
        k8s_client.apps_v1.patch_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )

        result = await secret_manager.inject_vault_agent_to_statefulset(
            statefulset_name="test-sts",
            namespace="test-ns",
            vault_role="test-vault-role",
            secret_configs=[
                {"name": "db-creds", "path": "secret/data/app/db"},
            ],
        )

        assert result == mock_statefulset
        k8s_client.apps_v1.patch_namespaced_stateful_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_inject_vault_agent_failure(
        self, secret_manager, k8s_client
    ):
        """Vault Agent 주입 실패 테스트"""
        k8s_client.apps_v1.patch_namespaced_deployment = AsyncMock(
            side_effect=Exception("K8s API error")
        )

        with pytest.raises(VaultInjectionException) as exc_info:
            await secret_manager.inject_vault_agent_to_deployment(
                deployment_name="test-deployment",
                namespace="test-ns",
                vault_role="test-vault-role",
                secret_configs=[
                    {"name": "db-creds", "path": "secret/data/app/db"},
                ],
            )

        assert "K8s API error" in str(exc_info.value)


class TestIntegratedSetup:
    """통합 설정 테스트"""

    @pytest.mark.asyncio
    async def test_setup_secret_access_without_workload(
        self, secret_manager, k8s_client, vault_client
    ):
        """Workload 없이 Secret 접근 설정 테스트"""
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock()

        result = await secret_manager.setup_secret_access(
            service_account_name="test-sa",
            namespace="test-ns",
            secret_paths=["secret/data/app/db"],
        )

        assert result["vault_role"] == "test-ns-test-sa-role"
        assert result["workload_updated"] is False

    @pytest.mark.asyncio
    async def test_setup_secret_access_with_deployment(
        self, secret_manager, k8s_client, vault_client
    ):
        """Deployment와 함께 Secret 접근 설정 테스트"""
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock()
        k8s_client.apps_v1.patch_namespaced_deployment = AsyncMock(
            return_value=V1Deployment()
        )

        result = await secret_manager.setup_secret_access(
            service_account_name="test-sa",
            namespace="test-ns",
            secret_paths=["secret/data/app/db"],
            workload_name="test-deployment",
            workload_type="deployment",
            secret_configs=[{"name": "db", "path": "secret/data/app/db"}],
        )

        assert result["vault_role"] == "test-ns-test-sa-role"
        assert result["workload_updated"] is True

    @pytest.mark.asyncio
    async def test_teardown_secret_access(
        self, secret_manager, k8s_client, vault_client, mock_service_account
    ):
        """Secret 접근 설정 제거 테스트"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock()

        result = await secret_manager.teardown_secret_access(
            service_account_name="test-sa",
            namespace="test-ns",
        )

        assert result is True
