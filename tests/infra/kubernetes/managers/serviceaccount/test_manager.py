"""ServiceAccountManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1ServiceAccount,
    V1ObjectMeta,
    V1LocalObjectReference,
    V1ServiceAccountList,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra import (
    ServiceAccountManager,
    ServiceAccountCreationException,
    ServiceAccountReadException,
    ServiceAccountUpdateException,
    ServiceAccountDeletionException,
    ServiceAccountListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClientImpl Mock 픽스처"""
    client = MagicMock(spec=KubernetesClientImpl)
    client.core_v1 = AsyncMock()
    return client


@pytest.fixture
def sa_manager(k8s_client):
    """ServiceAccountManager 픽스처"""
    return ServiceAccountManager(k8s_client)


@pytest.fixture
def mock_service_account():
    """Mock V1ServiceAccount 객체"""
    return V1ServiceAccount(
        api_version="v1",
        kind="ServiceAccount",
        metadata=V1ObjectMeta(
            name="test-sa",
            namespace="test-ns",
            labels={"app_deployment": "test"},
            annotations={"key": "value"},
        ),
        image_pull_secrets=[V1LocalObjectReference(name="docker-secret")],
    )


class TestServiceAccountManagerInit:
    """ServiceAccountManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = ServiceAccountManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = ServiceAccountManager(k8s_client)
        assert manager.logger is not None


class TestCreateServiceAccount:
    """ServiceAccount 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_service_account_success(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """ServiceAccount 생성 성공"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )

        result = await sa_manager.create_service_account(
            name="test-sa",
            namespace="test-ns",
            labels={"app_deployment": "test"},
            annotations={"key": "value"},
            image_pull_secrets=["docker-secret"],
        )

        assert result == mock_service_account
        k8s_client.core_v1.create_namespaced_service_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_service_account_already_exists(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """이미 존재하는 ServiceAccount 생성 (멱등성)"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )

        result = await sa_manager.create_service_account(
            name="test-sa",
            namespace="test-ns",
        )

        assert result == mock_service_account
        k8s_client.core_v1.create_namespaced_service_account.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_service_account_conflict_409(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_service_account,  # 재조회: 있음
            ]
        )
        k8s_client.core_v1.create_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await sa_manager.create_service_account(
            name="test-sa",
            namespace="test-ns",
        )

        assert result == mock_service_account
        assert k8s_client.core_v1.read_namespaced_service_account.call_count == 2

    @pytest.mark.asyncio
    async def test_create_service_account_api_exception(
        self, sa_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceAccountCreationException) as exc_info:
            await sa_manager.create_service_account(
                name="test-sa",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_service_account_unexpected_exception(
        self, sa_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_service_account = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ServiceAccountCreationException) as exc_info:
            await sa_manager.create_service_account(
                name="test-sa",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetServiceAccount:
    """ServiceAccount 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_service_account_success(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """ServiceAccount 조회 성공"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )

        result = await sa_manager.get_service_account(
            name="test-sa",
            namespace="test-ns",
        )

        assert result == mock_service_account

    @pytest.mark.asyncio
    async def test_get_service_account_not_found(
        self, sa_manager, k8s_client
    ):
        """존재하지 않는 ServiceAccount 조회 (404)"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await sa_manager.get_service_account(
            name="test-sa",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_service_account_api_exception(
        self, sa_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceAccountReadException) as exc_info:
            await sa_manager.get_service_account(
                name="test-sa",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_service_account_unexpected_exception(
        self, sa_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ServiceAccountReadException) as exc_info:
            await sa_manager.get_service_account(
                name="test-sa",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteServiceAccount:
    """ServiceAccount 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_service_account_success(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """ServiceAccount 삭제 성공"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.delete_namespaced_service_account = AsyncMock()

        result = await sa_manager.delete_service_account(
            name="test-sa",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_service_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_service_account_not_exists(
        self, sa_manager, k8s_client
    ):
        """존재하지 않는 ServiceAccount 삭제"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ServiceAccountDeletionException) as exc_info:
            await sa_manager.delete_service_account(
                name="test-sa",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_service_account_already_deleted_404(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.delete_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await sa_manager.delete_service_account(
            name="test-sa",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_service_account_api_exception(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.delete_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceAccountDeletionException) as exc_info:
            await sa_manager.delete_service_account(
                name="test-sa",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_service_account_with_grace_period(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """Grace period 지정 삭제"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.delete_namespaced_service_account = AsyncMock()

        result = await sa_manager.delete_service_account(
            name="test-sa",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_service_account.assert_called_once_with(
            name="test-sa",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListServiceAccounts:
    """ServiceAccount 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_service_accounts_in_namespace(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """특정 네임스페이스 내 ServiceAccount 목록 조회"""
        mock_list = V1ServiceAccountList(items=[mock_service_account])
        k8s_client.core_v1.list_namespaced_service_account = AsyncMock(
            return_value=mock_list
        )

        result = await sa_manager.list_service_accounts(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_service_account

    @pytest.mark.asyncio
    async def test_list_service_accounts_all_namespaces(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """전체 네임스페이스 ServiceAccount 목록 조회"""
        mock_list = V1ServiceAccountList(items=[mock_service_account])
        k8s_client.core_v1.list_service_account_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await sa_manager.list_service_accounts()

        assert len(result) == 1
        assert result[0] == mock_service_account

    @pytest.mark.asyncio
    async def test_list_service_accounts_with_selectors(
        self, sa_manager, k8s_client
    ):
        """셀렉터를 사용한 ServiceAccount 목록 조회"""
        mock_list = V1ServiceAccountList(items=[])
        k8s_client.core_v1.list_namespaced_service_account = AsyncMock(
            return_value=mock_list
        )

        result = await sa_manager.list_service_accounts(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-sa",
        )

        assert len(result) == 0
        k8s_client.core_v1.list_namespaced_service_account.assert_called_once_with(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-sa",
        )

    @pytest.mark.asyncio
    async def test_list_service_accounts_api_exception(
        self, sa_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.list_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceAccountListException) as exc_info:
            await sa_manager.list_service_accounts(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """ServiceAccount 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """ServiceAccount 존재함"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )

        result = await sa_manager.exists(name="test-sa", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, sa_manager, k8s_client):
        """ServiceAccount 존재하지 않음"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await sa_manager.exists(name="test-sa", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """ServiceAccount 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """레이블 병합 업데이트"""
        updated_sa = V1ServiceAccount(
            metadata=V1ObjectMeta(
                name="test-sa",
                namespace="test-ns",
                labels={"app_deployment": "test", "env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock(
            return_value=updated_sa
        )

        result = await sa_manager.update_labels(
            name="test-sa",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_sa
        k8s_client.core_v1.patch_namespaced_service_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """레이블 교체 업데이트"""
        updated_sa = V1ServiceAccount(
            metadata=V1ObjectMeta(
                name="test-sa",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock(
            return_value=updated_sa
        )

        result = await sa_manager.update_labels(
            name="test-sa",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_sa

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, sa_manager, k8s_client):
        """존재하지 않는 ServiceAccount 레이블 업데이트"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ServiceAccountUpdateException) as exc_info:
            await sa_manager.update_labels(
                name="test-sa",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceAccountUpdateException) as exc_info:
            await sa_manager.update_labels(
                name="test-sa",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestUpdateAnnotations:
    """ServiceAccount 어노테이션 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_annotations_merge(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """어노테이션 병합 업데이트"""
        updated_sa = V1ServiceAccount(
            metadata=V1ObjectMeta(
                name="test-sa",
                namespace="test-ns",
                annotations={"key": "value", "new-key": "new-value"},
            )
        )

        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock(
            return_value=updated_sa
        )

        result = await sa_manager.update_annotations(
            name="test-sa",
            namespace="test-ns",
            annotations={"new-key": "new-value"},
            merge=True,
        )

        assert result == updated_sa

    @pytest.mark.asyncio
    async def test_update_annotations_replace(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """어노테이션 교체 업데이트"""
        updated_sa = V1ServiceAccount(
            metadata=V1ObjectMeta(
                name="test-sa",
                namespace="test-ns",
                annotations={"new-key": "new-value"},
            )
        )

        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock(
            return_value=updated_sa
        )

        result = await sa_manager.update_annotations(
            name="test-sa",
            namespace="test-ns",
            annotations={"new-key": "new-value"},
            merge=False,
        )

        assert result == updated_sa

    @pytest.mark.asyncio
    async def test_update_annotations_not_found(self, sa_manager, k8s_client):
        """존재하지 않는 ServiceAccount 어노테이션 업데이트"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ServiceAccountUpdateException) as exc_info:
            await sa_manager.update_annotations(
                name="test-sa",
                namespace="test-ns",
                annotations={"key": "value"},
            )

        assert "does not exist" in str(exc_info.value)


class TestAddImagePullSecret:
    """ImagePullSecret 추가 테스트"""

    @pytest.mark.asyncio
    async def test_add_image_pull_secret_success(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """ImagePullSecret 추가 성공"""
        # 기존 SA에는 docker-secret이 이미 있음
        updated_sa = V1ServiceAccount(
            metadata=V1ObjectMeta(name="test-sa", namespace="test-ns"),
            image_pull_secrets=[
                V1LocalObjectReference(name="docker-secret"),
                V1LocalObjectReference(name="new-secret"),
            ],
        )

        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock(
            return_value=updated_sa
        )

        result = await sa_manager.add_image_pull_secret(
            name="test-sa",
            namespace="test-ns",
            secret_name="new-secret",
        )

        assert result == updated_sa
        k8s_client.core_v1.patch_namespaced_service_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_image_pull_secret_already_exists(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """이미 존재하는 ImagePullSecret 추가 (멱등성)"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )

        result = await sa_manager.add_image_pull_secret(
            name="test-sa",
            namespace="test-ns",
            secret_name="docker-secret",  # 이미 존재하는 secret
        )

        assert result == mock_service_account
        k8s_client.core_v1.patch_namespaced_service_account.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_image_pull_secret_not_found(
        self, sa_manager, k8s_client
    ):
        """존재하지 않는 ServiceAccount에 ImagePullSecret 추가"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ServiceAccountUpdateException) as exc_info:
            await sa_manager.add_image_pull_secret(
                name="test-sa",
                namespace="test-ns",
                secret_name="new-secret",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_image_pull_secret_api_exception(
        self, sa_manager, k8s_client, mock_service_account
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service_account = AsyncMock(
            return_value=mock_service_account
        )
        k8s_client.core_v1.patch_namespaced_service_account = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceAccountUpdateException) as exc_info:
            await sa_manager.add_image_pull_secret(
                name="test-sa",
                namespace="test-ns",
                secret_name="new-secret",
            )

        assert "Internal Server Error" in str(exc_info.value)
