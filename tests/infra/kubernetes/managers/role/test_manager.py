"""RoleManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1Role,
    V1ObjectMeta,
    V1PolicyRule,
    V1RoleList,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra.kubernetes.managers.role import (
    RoleManager,
    RoleCreationException,
    RoleReadException,
    RoleUpdateException,
    RoleDeletionException,
    RoleListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClientImpl Mock 픽스처"""
    client = MagicMock(spec=KubernetesClientImpl)
    client.rbac_v1 = AsyncMock()
    return client


@pytest.fixture
def role_manager(k8s_client):
    """RoleManager 픽스처"""
    return RoleManager(k8s_client)


@pytest.fixture
def mock_role():
    """Mock V1Role 객체"""
    return V1Role(
        api_version="rbac.authorization.k8s.io/v1",
        kind="Role",
        metadata=V1ObjectMeta(
            name="test-role",
            namespace="test-ns",
            labels={"app_deployment": "test"},
        ),
        rules=[
            V1PolicyRule(
                api_groups=[""],
                resources=["pods"],
                verbs=["get", "list"],
            )
        ],
    )


class TestRoleManagerInit:
    """RoleManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = RoleManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = RoleManager(k8s_client)
        assert manager.logger is not None


class TestCreateRole:
    """Role 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_role_success(self, role_manager, k8s_client, mock_role):
        """Role 생성 성공"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.rbac_v1.create_namespaced_role = AsyncMock(return_value=mock_role)

        result = await role_manager.create_role(
            name="test-role",
            namespace="test-ns",
            rules=[{"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list"]}],
            labels={"app_deployment": "test"},
        )

        assert result == mock_role
        k8s_client.rbac_v1.create_namespaced_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_role_already_exists(
        self, role_manager, k8s_client, mock_role
    ):
        """이미 존재하는 Role 생성 (멱등성)"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)

        result = await role_manager.create_role(
            name="test-role",
            namespace="test-ns",
            rules=[{"apiGroups": [""], "resources": ["pods"], "verbs": ["get"]}],
        )

        assert result == mock_role
        k8s_client.rbac_v1.create_namespaced_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_role_conflict_409(
        self, role_manager, k8s_client, mock_role
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_role,  # 재조회: 있음
            ]
        )
        k8s_client.rbac_v1.create_namespaced_role = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await role_manager.create_role(
            name="test-role",
            namespace="test-ns",
            rules=[{"apiGroups": [""], "resources": ["pods"], "verbs": ["get"]}],
        )

        assert result == mock_role
        assert k8s_client.rbac_v1.read_namespaced_role.call_count == 2

    @pytest.mark.asyncio
    async def test_create_role_api_exception(self, role_manager, k8s_client):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.rbac_v1.create_namespaced_role = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleCreationException) as exc_info:
            await role_manager.create_role(
                name="test-role",
                namespace="test-ns",
                rules=[{"apiGroups": [""], "resources": ["pods"], "verbs": ["get"]}],
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_role_unexpected_exception(self, role_manager, k8s_client):
        """예상치 못한 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.rbac_v1.create_namespaced_role = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(RoleCreationException) as exc_info:
            await role_manager.create_role(
                name="test-role",
                namespace="test-ns",
                rules=[{"apiGroups": [""], "resources": ["pods"], "verbs": ["get"]}],
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetRole:
    """Role 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_role_success(self, role_manager, k8s_client, mock_role):
        """Role 조회 성공"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)

        result = await role_manager.get_role(name="test-role", namespace="test-ns")

        assert result == mock_role

    @pytest.mark.asyncio
    async def test_get_role_not_found(self, role_manager, k8s_client):
        """존재하지 않는 Role 조회 (404)"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await role_manager.get_role(name="test-role", namespace="test-ns")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_role_api_exception(self, role_manager, k8s_client):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleReadException) as exc_info:
            await role_manager.get_role(name="test-role", namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_role_unexpected_exception(self, role_manager, k8s_client):
        """예상치 못한 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(RoleReadException) as exc_info:
            await role_manager.get_role(name="test-role", namespace="test-ns")

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteRole:
    """Role 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_role_success(self, role_manager, k8s_client, mock_role):
        """Role 삭제 성공"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)
        k8s_client.rbac_v1.delete_namespaced_role = AsyncMock()

        result = await role_manager.delete_role(name="test-role", namespace="test-ns")

        assert result is True
        k8s_client.rbac_v1.delete_namespaced_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_role_not_exists(self, role_manager, k8s_client):
        """존재하지 않는 Role 삭제"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(RoleDeletionException) as exc_info:
            await role_manager.delete_role(name="test-role", namespace="test-ns")

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_role_already_deleted_404(
        self, role_manager, k8s_client, mock_role
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)
        k8s_client.rbac_v1.delete_namespaced_role = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await role_manager.delete_role(name="test-role", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_role_api_exception(
        self, role_manager, k8s_client, mock_role
    ):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)
        k8s_client.rbac_v1.delete_namespaced_role = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleDeletionException) as exc_info:
            await role_manager.delete_role(name="test-role", namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_role_with_grace_period(
        self, role_manager, k8s_client, mock_role
    ):
        """Grace period 지정 삭제"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)
        k8s_client.rbac_v1.delete_namespaced_role = AsyncMock()

        result = await role_manager.delete_role(
            name="test-role", namespace="test-ns", grace_period_seconds=30
        )

        assert result is True
        k8s_client.rbac_v1.delete_namespaced_role.assert_called_once_with(
            name="test-role", namespace="test-ns", grace_period_seconds=30
        )


class TestListRoles:
    """Role 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_roles_in_namespace(
        self, role_manager, k8s_client, mock_role
    ):
        """특정 네임스페이스 내 Role 목록 조회"""
        mock_list = V1RoleList(items=[mock_role])
        k8s_client.rbac_v1.list_namespaced_role = AsyncMock(return_value=mock_list)

        result = await role_manager.list_roles(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_role

    @pytest.mark.asyncio
    async def test_list_roles_all_namespaces(
        self, role_manager, k8s_client, mock_role
    ):
        """전체 네임스페이스 Role 목록 조회"""
        mock_list = V1RoleList(items=[mock_role])
        k8s_client.rbac_v1.list_role_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await role_manager.list_roles()

        assert len(result) == 1
        assert result[0] == mock_role

    @pytest.mark.asyncio
    async def test_list_roles_with_selectors(self, role_manager, k8s_client):
        """셀렉터를 사용한 Role 목록 조회"""
        mock_list = V1RoleList(items=[])
        k8s_client.rbac_v1.list_namespaced_role = AsyncMock(return_value=mock_list)

        result = await role_manager.list_roles(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-role",
        )

        assert len(result) == 0
        k8s_client.rbac_v1.list_namespaced_role.assert_called_once_with(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-role",
        )

    @pytest.mark.asyncio
    async def test_list_roles_api_exception(self, role_manager, k8s_client):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.list_namespaced_role = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleListException) as exc_info:
            await role_manager.list_roles(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """Role 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(self, role_manager, k8s_client, mock_role):
        """Role 존재함"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)

        result = await role_manager.exists(name="test-role", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, role_manager, k8s_client):
        """Role 존재하지 않음"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await role_manager.exists(name="test-role", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """Role 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(self, role_manager, k8s_client, mock_role):
        """레이블 병합 업데이트"""
        updated_role = V1Role(
            metadata=V1ObjectMeta(
                name="test-role",
                namespace="test-ns",
                labels={"app_deployment": "test", "env": "prod"},
            )
        )

        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)
        k8s_client.rbac_v1.patch_namespaced_role = AsyncMock(return_value=updated_role)

        result = await role_manager.update_labels(
            name="test-role",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_role
        k8s_client.rbac_v1.patch_namespaced_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(self, role_manager, k8s_client, mock_role):
        """레이블 교체 업데이트"""
        updated_role = V1Role(
            metadata=V1ObjectMeta(
                name="test-role", namespace="test-ns", labels={"env": "prod"}
            )
        )

        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)
        k8s_client.rbac_v1.patch_namespaced_role = AsyncMock(return_value=updated_role)

        result = await role_manager.update_labels(
            name="test-role",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_role

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, role_manager, k8s_client):
        """존재하지 않는 Role 레이블 업데이트"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(RoleUpdateException) as exc_info:
            await role_manager.update_labels(
                name="test-role", namespace="test-ns", labels={"env": "prod"}
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, role_manager, k8s_client, mock_role
    ):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role = AsyncMock(return_value=mock_role)
        k8s_client.rbac_v1.patch_namespaced_role = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleUpdateException) as exc_info:
            await role_manager.update_labels(
                name="test-role", namespace="test-ns", labels={"env": "prod"}
            )

        assert "Internal Server Error" in str(exc_info.value)
