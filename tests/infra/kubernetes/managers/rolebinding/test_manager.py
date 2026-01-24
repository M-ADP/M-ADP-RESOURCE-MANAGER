"""RoleBindingManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1RoleBinding,
    V1ObjectMeta,
    V1RoleRef,
    RbacV1Subject,
    V1RoleBindingList,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra.kubernetes.managers.rolebinding import (
    RoleBindingManager,
    RoleBindingCreationException,
    RoleBindingReadException,
    RoleBindingUpdateException,
    RoleBindingDeletionException,
    RoleBindingListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClientImpl Mock 픽스처"""
    client = MagicMock(spec=KubernetesClientImpl)
    client.rbac_v1 = AsyncMock()
    return client


@pytest.fixture
def rb_manager(k8s_client):
    """RoleBindingManager 픽스처"""
    return RoleBindingManager(k8s_client)


@pytest.fixture
def mock_rolebinding():
    """Mock V1RoleBinding 객체"""
    return V1RoleBinding(
        api_version="rbac.authorization.k8s.io/v1",
        kind="RoleBinding",
        metadata=V1ObjectMeta(
            name="test-rb",
            namespace="test-ns",
            labels={"app": "test"},
        ),
        role_ref=V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind="Role",
            name="test-role",
        ),
        subjects=[
            RbacV1Subject(
                kind="ServiceAccount",
                name="test-sa",
                namespace="test-ns",
            )
        ],
    )


class TestRoleBindingManagerInit:
    """RoleBindingManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = RoleBindingManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = RoleBindingManager(k8s_client)
        assert manager.logger is not None


class TestCreateRoleBinding:
    """RoleBinding 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_rolebinding_success(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """RoleBinding 생성 성공"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.rbac_v1.create_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )

        result = await rb_manager.create_rolebinding(
            name="test-rb",
            namespace="test-ns",
            role_name="test-role",
            subjects=[{"kind": "ServiceAccount", "name": "test-sa", "namespace": "test-ns"}],
            labels={"app": "test"},
        )

        assert result == mock_rolebinding
        k8s_client.rbac_v1.create_namespaced_role_binding.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_rolebinding_already_exists(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """이미 존재하는 RoleBinding 생성 (멱등성)"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )

        result = await rb_manager.create_rolebinding(
            name="test-rb",
            namespace="test-ns",
            role_name="test-role",
            subjects=[{"kind": "ServiceAccount", "name": "test-sa"}],
        )

        assert result == mock_rolebinding
        k8s_client.rbac_v1.create_namespaced_role_binding.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_rolebinding_conflict_409(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_rolebinding,  # 재조회: 있음
            ]
        )
        k8s_client.rbac_v1.create_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await rb_manager.create_rolebinding(
            name="test-rb",
            namespace="test-ns",
            role_name="test-role",
            subjects=[{"kind": "ServiceAccount", "name": "test-sa"}],
        )

        assert result == mock_rolebinding
        assert k8s_client.rbac_v1.read_namespaced_role_binding.call_count == 2

    @pytest.mark.asyncio
    async def test_create_rolebinding_api_exception(self, rb_manager, k8s_client):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.rbac_v1.create_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleBindingCreationException) as exc_info:
            await rb_manager.create_rolebinding(
                name="test-rb",
                namespace="test-ns",
                role_name="test-role",
                subjects=[{"kind": "ServiceAccount", "name": "test-sa"}],
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_rolebinding_unexpected_exception(
        self, rb_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.rbac_v1.create_namespaced_role_binding = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(RoleBindingCreationException) as exc_info:
            await rb_manager.create_rolebinding(
                name="test-rb",
                namespace="test-ns",
                role_name="test-role",
                subjects=[{"kind": "ServiceAccount", "name": "test-sa"}],
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetRoleBinding:
    """RoleBinding 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_rolebinding_success(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """RoleBinding 조회 성공"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )

        result = await rb_manager.get_rolebinding(name="test-rb", namespace="test-ns")

        assert result == mock_rolebinding

    @pytest.mark.asyncio
    async def test_get_rolebinding_not_found(self, rb_manager, k8s_client):
        """존재하지 않는 RoleBinding 조회 (404)"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rb_manager.get_rolebinding(name="test-rb", namespace="test-ns")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_rolebinding_api_exception(self, rb_manager, k8s_client):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleBindingReadException) as exc_info:
            await rb_manager.get_rolebinding(name="test-rb", namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_rolebinding_unexpected_exception(self, rb_manager, k8s_client):
        """예상치 못한 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(RoleBindingReadException) as exc_info:
            await rb_manager.get_rolebinding(name="test-rb", namespace="test-ns")

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteRoleBinding:
    """RoleBinding 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_rolebinding_success(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """RoleBinding 삭제 성공"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )
        k8s_client.rbac_v1.delete_namespaced_role_binding = AsyncMock()

        result = await rb_manager.delete_rolebinding(
            name="test-rb", namespace="test-ns"
        )

        assert result is True
        k8s_client.rbac_v1.delete_namespaced_role_binding.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_rolebinding_not_exists(self, rb_manager, k8s_client):
        """존재하지 않는 RoleBinding 삭제"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(RoleBindingDeletionException) as exc_info:
            await rb_manager.delete_rolebinding(name="test-rb", namespace="test-ns")

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_rolebinding_already_deleted_404(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )
        k8s_client.rbac_v1.delete_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rb_manager.delete_rolebinding(
            name="test-rb", namespace="test-ns"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_rolebinding_api_exception(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )
        k8s_client.rbac_v1.delete_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleBindingDeletionException) as exc_info:
            await rb_manager.delete_rolebinding(name="test-rb", namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_rolebinding_with_grace_period(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """Grace period 지정 삭제"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )
        k8s_client.rbac_v1.delete_namespaced_role_binding = AsyncMock()

        result = await rb_manager.delete_rolebinding(
            name="test-rb", namespace="test-ns", grace_period_seconds=30
        )

        assert result is True
        k8s_client.rbac_v1.delete_namespaced_role_binding.assert_called_once_with(
            name="test-rb", namespace="test-ns", grace_period_seconds=30
        )


class TestListRoleBindings:
    """RoleBinding 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_rolebindings_in_namespace(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """특정 네임스페이스 내 RoleBinding 목록 조회"""
        mock_list = V1RoleBindingList(items=[mock_rolebinding])
        k8s_client.rbac_v1.list_namespaced_role_binding = AsyncMock(
            return_value=mock_list
        )

        result = await rb_manager.list_rolebindings(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_rolebinding

    @pytest.mark.asyncio
    async def test_list_rolebindings_all_namespaces(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """전체 네임스페이스 RoleBinding 목록 조회"""
        mock_list = V1RoleBindingList(items=[mock_rolebinding])
        k8s_client.rbac_v1.list_role_binding_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await rb_manager.list_rolebindings()

        assert len(result) == 1
        assert result[0] == mock_rolebinding

    @pytest.mark.asyncio
    async def test_list_rolebindings_with_selectors(self, rb_manager, k8s_client):
        """셀렉터를 사용한 RoleBinding 목록 조회"""
        mock_list = V1RoleBindingList(items=[])
        k8s_client.rbac_v1.list_namespaced_role_binding = AsyncMock(
            return_value=mock_list
        )

        result = await rb_manager.list_rolebindings(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-rb",
        )

        assert len(result) == 0
        k8s_client.rbac_v1.list_namespaced_role_binding.assert_called_once_with(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-rb",
        )

    @pytest.mark.asyncio
    async def test_list_rolebindings_api_exception(self, rb_manager, k8s_client):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.list_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleBindingListException) as exc_info:
            await rb_manager.list_rolebindings(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """RoleBinding 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(self, rb_manager, k8s_client, mock_rolebinding):
        """RoleBinding 존재함"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )

        result = await rb_manager.exists(name="test-rb", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, rb_manager, k8s_client):
        """RoleBinding 존재하지 않음"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rb_manager.exists(name="test-rb", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """RoleBinding 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """레이블 병합 업데이트"""
        updated_rb = V1RoleBinding(
            metadata=V1ObjectMeta(
                name="test-rb",
                namespace="test-ns",
                labels={"app": "test", "env": "prod"},
            ),
            role_ref=V1RoleRef(
                api_group="rbac.authorization.k8s.io",
                kind="Role",
                name="test-role",
            ),
        )

        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )
        k8s_client.rbac_v1.patch_namespaced_role_binding = AsyncMock(
            return_value=updated_rb
        )

        result = await rb_manager.update_labels(
            name="test-rb",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_rb
        k8s_client.rbac_v1.patch_namespaced_role_binding.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """레이블 교체 업데이트"""
        updated_rb = V1RoleBinding(
            metadata=V1ObjectMeta(
                name="test-rb", namespace="test-ns", labels={"env": "prod"}
            ),
            role_ref=V1RoleRef(
                api_group="rbac.authorization.k8s.io",
                kind="Role",
                name="test-role",
            ),
        )

        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )
        k8s_client.rbac_v1.patch_namespaced_role_binding = AsyncMock(
            return_value=updated_rb
        )

        result = await rb_manager.update_labels(
            name="test-rb",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_rb

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, rb_manager, k8s_client):
        """존재하지 않는 RoleBinding 레이블 업데이트"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(RoleBindingUpdateException) as exc_info:
            await rb_manager.update_labels(
                name="test-rb", namespace="test-ns", labels={"env": "prod"}
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )
        k8s_client.rbac_v1.patch_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleBindingUpdateException) as exc_info:
            await rb_manager.update_labels(
                name="test-rb", namespace="test-ns", labels={"env": "prod"}
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestAddSubject:
    """Subject 추가 테스트"""

    @pytest.mark.asyncio
    async def test_add_subject_success(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """Subject 추가 성공"""
        updated_rb = V1RoleBinding(
            metadata=V1ObjectMeta(name="test-rb", namespace="test-ns"),
            role_ref=V1RoleRef(
                api_group="rbac.authorization.k8s.io",
                kind="Role",
                name="test-role",
            ),
            subjects=[
                RbacV1Subject(
                    kind="ServiceAccount", name="test-sa", namespace="test-ns"
                ),
                RbacV1Subject(kind="User", name="test-user"),
            ],
        )

        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )
        k8s_client.rbac_v1.patch_namespaced_role_binding = AsyncMock(
            return_value=updated_rb
        )

        result = await rb_manager.add_subject(
            name="test-rb",
            namespace="test-ns",
            subject={"kind": "User", "name": "test-user"},
        )

        assert result == updated_rb
        k8s_client.rbac_v1.patch_namespaced_role_binding.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_subject_already_exists(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """이미 존재하는 Subject 추가 (멱등성)"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )

        result = await rb_manager.add_subject(
            name="test-rb",
            namespace="test-ns",
            subject={"kind": "ServiceAccount", "name": "test-sa", "namespace": "test-ns"},
        )

        assert result == mock_rolebinding
        k8s_client.rbac_v1.patch_namespaced_role_binding.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_subject_not_found(self, rb_manager, k8s_client):
        """존재하지 않는 RoleBinding에 Subject 추가"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(RoleBindingUpdateException) as exc_info:
            await rb_manager.add_subject(
                name="test-rb",
                namespace="test-ns",
                subject={"kind": "User", "name": "test-user"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_subject_api_exception(
        self, rb_manager, k8s_client, mock_rolebinding
    ):
        """API 예외 발생 시"""
        k8s_client.rbac_v1.read_namespaced_role_binding = AsyncMock(
            return_value=mock_rolebinding
        )
        k8s_client.rbac_v1.patch_namespaced_role_binding = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(RoleBindingUpdateException) as exc_info:
            await rb_manager.add_subject(
                name="test-rb",
                namespace="test-ns",
                subject={"kind": "User", "name": "test-user"},
            )

        assert "Internal Server Error" in str(exc_info.value)
