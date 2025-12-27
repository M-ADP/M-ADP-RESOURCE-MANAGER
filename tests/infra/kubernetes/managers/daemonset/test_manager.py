"""DaemonSetManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1DaemonSet,
    V1ObjectMeta,
    V1DaemonSetSpec,
    V1DaemonSetList,
    V1LabelSelector,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
    V1DaemonSetStatus,
    V1DaemonSetCondition,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from infra.kubernetes.managers.daemonset import (
    DaemonSetManager,
    DaemonSetCreationException,
    DaemonSetReadException,
    DaemonSetUpdateException,
    DaemonSetDeletionException,
    DaemonSetListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClient Mock 픽스처"""
    client = MagicMock(spec=KubernetesClient)
    client.apps_v1 = AsyncMock()
    return client


@pytest.fixture
def ds_manager(k8s_client):
    """DaemonSetManager 픽스처"""
    return DaemonSetManager(k8s_client)


@pytest.fixture
def mock_container():
    """Mock V1Container 객체"""
    return V1Container(
        name="test-container",
        image="nginx:latest",
        ports=[],
    )


@pytest.fixture
def mock_daemonset(mock_container):
    """Mock V1DaemonSet 객체"""
    return V1DaemonSet(
        api_version="apps/v1",
        kind="DaemonSet",
        metadata=V1ObjectMeta(
            name="test-daemonset",
            namespace="test-ns",
            labels={"app": "test"},
            annotations={"key": "value"},
        ),
        spec=V1DaemonSetSpec(
            selector=V1LabelSelector(
                match_labels={"app": "test"},
            ),
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(
                    labels={"app": "test"},
                ),
                spec=V1PodSpec(
                    containers=[mock_container],
                ),
            ),
        ),
        status=V1DaemonSetStatus(
            current_number_scheduled=3,
            desired_number_scheduled=3,
            number_available=3,
            number_misscheduled=0,
            number_ready=3,
            number_unavailable=0,
            updated_number_scheduled=3,
            conditions=[
                V1DaemonSetCondition(
                    type="Available",
                    status="True",
                    reason="MinimumAvailable",
                    message="DaemonSet has minimum availability.",
                )
            ],
        ),
    )


class TestDaemonSetManagerInit:
    """DaemonSetManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = DaemonSetManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = DaemonSetManager(k8s_client)
        assert manager.logger is not None


class TestCreateDaemonSet:
    """DaemonSet 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_daemonset_success(
        self, ds_manager, k8s_client, mock_daemonset, mock_container
    ):
        """DaemonSet 생성 성공"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )

        result = await ds_manager.create_daemonset(
            name="test-daemonset",
            namespace="test-ns",
            containers=[mock_container],
            labels={"app": "test"},
            annotations={"key": "value"},
        )

        assert result == mock_daemonset
        k8s_client.apps_v1.create_namespaced_daemon_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_daemonset_already_exists(
        self, ds_manager, k8s_client, mock_daemonset, mock_container
    ):
        """이미 존재하는 DaemonSet 생성 (멱등성)"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )

        result = await ds_manager.create_daemonset(
            name="test-daemonset",
            namespace="test-ns",
            containers=[mock_container],
        )

        assert result == mock_daemonset
        k8s_client.apps_v1.create_namespaced_daemon_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_daemonset_conflict_409(
        self, ds_manager, k8s_client, mock_daemonset, mock_container
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_daemonset,  # 재조회: 있음
            ]
        )
        k8s_client.apps_v1.create_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await ds_manager.create_daemonset(
            name="test-daemonset",
            namespace="test-ns",
            containers=[mock_container],
        )

        assert result == mock_daemonset
        assert k8s_client.apps_v1.read_namespaced_daemon_set.call_count == 2

    @pytest.mark.asyncio
    async def test_create_daemonset_api_exception(
        self, ds_manager, k8s_client, mock_container
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DaemonSetCreationException) as exc_info:
            await ds_manager.create_daemonset(
                name="test-daemonset",
                namespace="test-ns",
                containers=[mock_container],
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_daemonset_unexpected_exception(
        self, ds_manager, k8s_client, mock_container
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_daemon_set = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(DaemonSetCreationException) as exc_info:
            await ds_manager.create_daemonset(
                name="test-daemonset",
                namespace="test-ns",
                containers=[mock_container],
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetDaemonSet:
    """DaemonSet 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_daemonset_success(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """DaemonSet 조회 성공"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )

        result = await ds_manager.get_daemonset(
            name="test-daemonset",
            namespace="test-ns",
        )

        assert result == mock_daemonset

    @pytest.mark.asyncio
    async def test_get_daemonset_not_found(
        self, ds_manager, k8s_client
    ):
        """존재하지 않는 DaemonSet 조회 (404)"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await ds_manager.get_daemonset(
            name="test-daemonset",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_daemonset_api_exception(
        self, ds_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DaemonSetReadException) as exc_info:
            await ds_manager.get_daemonset(
                name="test-daemonset",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_daemonset_unexpected_exception(
        self, ds_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(DaemonSetReadException) as exc_info:
            await ds_manager.get_daemonset(
                name="test-daemonset",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteDaemonSet:
    """DaemonSet 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_daemonset_success(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """DaemonSet 삭제 성공"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )
        k8s_client.apps_v1.delete_namespaced_daemon_set = AsyncMock()

        result = await ds_manager.delete_daemonset(
            name="test-daemonset",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.apps_v1.delete_namespaced_daemon_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_daemonset_not_exists(
        self, ds_manager, k8s_client
    ):
        """존재하지 않는 DaemonSet 삭제"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(DaemonSetDeletionException) as exc_info:
            await ds_manager.delete_daemonset(
                name="test-daemonset",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_daemonset_already_deleted_404(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )
        k8s_client.apps_v1.delete_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await ds_manager.delete_daemonset(
            name="test-daemonset",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_daemonset_api_exception(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )
        k8s_client.apps_v1.delete_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DaemonSetDeletionException) as exc_info:
            await ds_manager.delete_daemonset(
                name="test-daemonset",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_daemonset_with_grace_period(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """Grace period 지정 삭제"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )
        k8s_client.apps_v1.delete_namespaced_daemon_set = AsyncMock()

        result = await ds_manager.delete_daemonset(
            name="test-daemonset",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.apps_v1.delete_namespaced_daemon_set.assert_called_once_with(
            name="test-daemonset",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListDaemonSets:
    """DaemonSet 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_daemonsets_in_namespace(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """특정 네임스페이스 내 DaemonSet 목록 조회"""
        mock_list = V1DaemonSetList(items=[mock_daemonset])
        k8s_client.apps_v1.list_namespaced_daemon_set = AsyncMock(
            return_value=mock_list
        )

        result = await ds_manager.list_daemonsets(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_daemonset

    @pytest.mark.asyncio
    async def test_list_daemonsets_all_namespaces(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """전체 네임스페이스 DaemonSet 목록 조회"""
        mock_list = V1DaemonSetList(items=[mock_daemonset])
        k8s_client.apps_v1.list_daemon_set_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await ds_manager.list_daemonsets()

        assert len(result) == 1
        assert result[0] == mock_daemonset

    @pytest.mark.asyncio
    async def test_list_daemonsets_with_selectors(
        self, ds_manager, k8s_client
    ):
        """셀렉터를 사용한 DaemonSet 목록 조회"""
        mock_list = V1DaemonSetList(items=[])
        k8s_client.apps_v1.list_namespaced_daemon_set = AsyncMock(
            return_value=mock_list
        )

        result = await ds_manager.list_daemonsets(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-daemonset",
        )

        assert len(result) == 0
        k8s_client.apps_v1.list_namespaced_daemon_set.assert_called_once_with(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-daemonset",
        )

    @pytest.mark.asyncio
    async def test_list_daemonsets_api_exception(
        self, ds_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.list_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DaemonSetListException) as exc_info:
            await ds_manager.list_daemonsets(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """DaemonSet 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """DaemonSet 존재함"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )

        result = await ds_manager.exists(name="test-daemonset", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, ds_manager, k8s_client):
        """DaemonSet 존재하지 않음"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await ds_manager.exists(name="test-daemonset", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """DaemonSet 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """레이블 병합 업데이트"""
        updated_ds = V1DaemonSet(
            metadata=V1ObjectMeta(
                name="test-daemonset",
                namespace="test-ns",
                labels={"app": "test", "env": "prod"},
            )
        )

        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )
        k8s_client.apps_v1.patch_namespaced_daemon_set = AsyncMock(
            return_value=updated_ds
        )

        result = await ds_manager.update_labels(
            name="test-daemonset",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_ds
        k8s_client.apps_v1.patch_namespaced_daemon_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """레이블 교체 업데이트"""
        updated_ds = V1DaemonSet(
            metadata=V1ObjectMeta(
                name="test-daemonset",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )
        k8s_client.apps_v1.patch_namespaced_daemon_set = AsyncMock(
            return_value=updated_ds
        )

        result = await ds_manager.update_labels(
            name="test-daemonset",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_ds

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, ds_manager, k8s_client):
        """존재하지 않는 DaemonSet 레이블 업데이트"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(DaemonSetUpdateException) as exc_info:
            await ds_manager.update_labels(
                name="test-daemonset",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )
        k8s_client.apps_v1.patch_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DaemonSetUpdateException) as exc_info:
            await ds_manager.update_labels(
                name="test-daemonset",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestGetDaemonSetStatus:
    """DaemonSet 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_daemonset_status_success(
        self, ds_manager, k8s_client, mock_daemonset
    ):
        """DaemonSet 상태 조회 성공"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=mock_daemonset
        )

        result = await ds_manager.get_daemonset_status(
            name="test-daemonset",
            namespace="test-ns",
        )

        assert result is not None
        assert result["current_number_scheduled"] == 3
        assert result["desired_number_scheduled"] == 3
        assert result["number_available"] == 3
        assert result["number_misscheduled"] == 0
        assert result["number_ready"] == 3
        assert result["number_unavailable"] == 0
        assert result["updated_number_scheduled"] == 3
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "Available"

    @pytest.mark.asyncio
    async def test_get_daemonset_status_not_found(
        self, ds_manager, k8s_client
    ):
        """존재하지 않는 DaemonSet 상태 조회"""
        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await ds_manager.get_daemonset_status(
            name="test-daemonset",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_daemonset_status_no_status(
        self, ds_manager, k8s_client
    ):
        """Status가 없는 DaemonSet"""
        daemonset_no_status = V1DaemonSet(
            metadata=V1ObjectMeta(
                name="test-daemonset",
                namespace="test-ns",
            ),
            spec=V1DaemonSetSpec(
                selector=V1LabelSelector(match_labels={"app": "test"}),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": "test"}),
                    spec=V1PodSpec(containers=[]),
                ),
            ),
        )

        k8s_client.apps_v1.read_namespaced_daemon_set = AsyncMock(
            return_value=daemonset_no_status
        )

        result = await ds_manager.get_daemonset_status(
            name="test-daemonset",
            namespace="test-ns",
        )

        assert result is None
