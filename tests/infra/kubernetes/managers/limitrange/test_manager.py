"""LimitRangeManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1LimitRange,
    V1ObjectMeta,
    V1LimitRangeSpec,
    V1LimitRangeItem,
    V1LimitRangeList,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra.kubernetes.managers.limitrange import (
    LimitRangeManager,
    LimitRangeCreationException,
    LimitRangeReadException,
    LimitRangeUpdateException,
    LimitRangeDeletionException,
    LimitRangeListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClientImpl Mock 픽스처"""
    client = MagicMock(spec=KubernetesClientImpl)
    client.core_v1 = AsyncMock()
    return client


@pytest.fixture
def lr_manager(k8s_client):
    """LimitRangeManager 픽스처"""
    return LimitRangeManager(k8s_client)


@pytest.fixture
def mock_limitrange():
    """Mock V1LimitRange 객체"""
    return V1LimitRange(
        api_version="v1",
        kind="LimitRange",
        metadata=V1ObjectMeta(
            name="test-lr",
            namespace="test-ns",
            labels={"app_deployment": "test"},
            annotations={"key": "value"},
        ),
        spec=V1LimitRangeSpec(
            limits=[
                V1LimitRangeItem(
                    type="Container",
                    max={"cpu": "2", "memory": "1Gi"},
                    min={"cpu": "100m", "memory": "128Mi"},
                    default={"cpu": "500m", "memory": "512Mi"},
                    default_request={"cpu": "200m", "memory": "256Mi"},
                )
            ]
        ),
    )


@pytest.fixture
def mock_limit_items():
    """Mock V1LimitRangeItem 리스트"""
    return [
        V1LimitRangeItem(
            type="Container",
            max={"cpu": "2", "memory": "1Gi"},
            min={"cpu": "100m", "memory": "128Mi"},
            default={"cpu": "500m", "memory": "512Mi"},
            default_request={"cpu": "200m", "memory": "256Mi"},
        )
    ]


class TestLimitRangeManagerInit:
    """LimitRangeManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = LimitRangeManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = LimitRangeManager(k8s_client)
        assert manager.logger is not None


class TestCreateLimitRange:
    """LimitRange 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_limitrange_success(
        self, lr_manager, k8s_client, mock_limitrange, mock_limit_items
    ):
        """LimitRange 생성 성공"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )

        result = await lr_manager.create_limitrange(
            name="test-lr",
            namespace="test-ns",
            limits=mock_limit_items,
            labels={"app_deployment": "test"},
            annotations={"key": "value"},
        )

        assert result == mock_limitrange
        k8s_client.core_v1.create_namespaced_limit_range.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_limitrange_already_exists(
        self, lr_manager, k8s_client, mock_limitrange, mock_limit_items
    ):
        """이미 존재하는 LimitRange 생성 (멱등성)"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )

        result = await lr_manager.create_limitrange(
            name="test-lr",
            namespace="test-ns",
            limits=mock_limit_items,
        )

        assert result == mock_limitrange
        k8s_client.core_v1.create_namespaced_limit_range.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_limitrange_conflict_409(
        self, lr_manager, k8s_client, mock_limitrange, mock_limit_items
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_limitrange,  # 재조회: 있음
            ]
        )
        k8s_client.core_v1.create_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await lr_manager.create_limitrange(
            name="test-lr",
            namespace="test-ns",
            limits=mock_limit_items,
        )

        assert result == mock_limitrange
        assert k8s_client.core_v1.read_namespaced_limit_range.call_count == 2

    @pytest.mark.asyncio
    async def test_create_limitrange_api_exception(
        self, lr_manager, k8s_client, mock_limit_items
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(LimitRangeCreationException) as exc_info:
            await lr_manager.create_limitrange(
                name="test-lr",
                namespace="test-ns",
                limits=mock_limit_items,
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_limitrange_unexpected_exception(
        self, lr_manager, k8s_client, mock_limit_items
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_limit_range = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(LimitRangeCreationException) as exc_info:
            await lr_manager.create_limitrange(
                name="test-lr",
                namespace="test-ns",
                limits=mock_limit_items,
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetLimitRange:
    """LimitRange 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_limitrange_success(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """LimitRange 조회 성공"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )

        result = await lr_manager.get_limitrange(
            name="test-lr",
            namespace="test-ns",
        )

        assert result == mock_limitrange

    @pytest.mark.asyncio
    async def test_get_limitrange_not_found(
        self, lr_manager, k8s_client
    ):
        """존재하지 않는 LimitRange 조회 (404)"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await lr_manager.get_limitrange(
            name="test-lr",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_limitrange_api_exception(
        self, lr_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(LimitRangeReadException) as exc_info:
            await lr_manager.get_limitrange(
                name="test-lr",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_limitrange_unexpected_exception(
        self, lr_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(LimitRangeReadException) as exc_info:
            await lr_manager.get_limitrange(
                name="test-lr",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteLimitRange:
    """LimitRange 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_limitrange_success(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """LimitRange 삭제 성공"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )
        k8s_client.core_v1.delete_namespaced_limit_range = AsyncMock()

        result = await lr_manager.delete_limitrange(
            name="test-lr",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_limit_range.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_limitrange_not_exists(
        self, lr_manager, k8s_client
    ):
        """존재하지 않는 LimitRange 삭제"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(LimitRangeDeletionException) as exc_info:
            await lr_manager.delete_limitrange(
                name="test-lr",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_limitrange_already_deleted_404(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )
        k8s_client.core_v1.delete_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await lr_manager.delete_limitrange(
            name="test-lr",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_limitrange_api_exception(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )
        k8s_client.core_v1.delete_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(LimitRangeDeletionException) as exc_info:
            await lr_manager.delete_limitrange(
                name="test-lr",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_limitrange_with_grace_period(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """Grace period 지정 삭제"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )
        k8s_client.core_v1.delete_namespaced_limit_range = AsyncMock()

        result = await lr_manager.delete_limitrange(
            name="test-lr",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_limit_range.assert_called_once_with(
            name="test-lr",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListLimitRanges:
    """LimitRange 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_limitranges_in_namespace(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """특정 네임스페이스 내 LimitRange 목록 조회"""
        mock_list = V1LimitRangeList(items=[mock_limitrange])
        k8s_client.core_v1.list_namespaced_limit_range = AsyncMock(
            return_value=mock_list
        )

        result = await lr_manager.list_limitranges(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_limitrange

    @pytest.mark.asyncio
    async def test_list_limitranges_all_namespaces(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """전체 네임스페이스 LimitRange 목록 조회"""
        mock_list = V1LimitRangeList(items=[mock_limitrange])
        k8s_client.core_v1.list_limit_range_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await lr_manager.list_limitranges()

        assert len(result) == 1
        assert result[0] == mock_limitrange

    @pytest.mark.asyncio
    async def test_list_limitranges_with_selectors(
        self, lr_manager, k8s_client
    ):
        """셀렉터를 사용한 LimitRange 목록 조회"""
        mock_list = V1LimitRangeList(items=[])
        k8s_client.core_v1.list_namespaced_limit_range = AsyncMock(
            return_value=mock_list
        )

        result = await lr_manager.list_limitranges(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-lr",
        )

        assert len(result) == 0
        k8s_client.core_v1.list_namespaced_limit_range.assert_called_once_with(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-lr",
        )

    @pytest.mark.asyncio
    async def test_list_limitranges_api_exception(
        self, lr_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.list_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(LimitRangeListException) as exc_info:
            await lr_manager.list_limitranges(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """LimitRange 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """LimitRange 존재함"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )

        result = await lr_manager.exists(name="test-lr", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, lr_manager, k8s_client):
        """LimitRange 존재하지 않음"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await lr_manager.exists(name="test-lr", namespace="test-ns")

        assert result is False


class TestUpdateLimits:
    """LimitRange 제한 사항 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_limits_success(
        self, lr_manager, k8s_client, mock_limitrange, mock_limit_items
    ):
        """제한 사항 업데이트 성공"""
        updated_lr = V1LimitRange(
            metadata=V1ObjectMeta(
                name="test-lr",
                namespace="test-ns",
            ),
            spec=V1LimitRangeSpec(limits=mock_limit_items),
        )

        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )
        k8s_client.core_v1.patch_namespaced_limit_range = AsyncMock(
            return_value=updated_lr
        )

        result = await lr_manager.update_limits(
            name="test-lr",
            namespace="test-ns",
            limits=mock_limit_items,
        )

        assert result == updated_lr
        k8s_client.core_v1.patch_namespaced_limit_range.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_limits_not_found(
        self, lr_manager, k8s_client, mock_limit_items
    ):
        """존재하지 않는 LimitRange 제한 사항 업데이트"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(LimitRangeUpdateException) as exc_info:
            await lr_manager.update_limits(
                name="test-lr",
                namespace="test-ns",
                limits=mock_limit_items,
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_limits_api_exception(
        self, lr_manager, k8s_client, mock_limitrange, mock_limit_items
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )
        k8s_client.core_v1.patch_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(LimitRangeUpdateException) as exc_info:
            await lr_manager.update_limits(
                name="test-lr",
                namespace="test-ns",
                limits=mock_limit_items,
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestUpdateLabels:
    """LimitRange 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """레이블 병합 업데이트"""
        updated_lr = V1LimitRange(
            metadata=V1ObjectMeta(
                name="test-lr",
                namespace="test-ns",
                labels={"app_deployment": "test", "env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )
        k8s_client.core_v1.patch_namespaced_limit_range = AsyncMock(
            return_value=updated_lr
        )

        result = await lr_manager.update_labels(
            name="test-lr",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_lr
        k8s_client.core_v1.patch_namespaced_limit_range.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """레이블 교체 업데이트"""
        updated_lr = V1LimitRange(
            metadata=V1ObjectMeta(
                name="test-lr",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )
        k8s_client.core_v1.patch_namespaced_limit_range = AsyncMock(
            return_value=updated_lr
        )

        result = await lr_manager.update_labels(
            name="test-lr",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_lr

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, lr_manager, k8s_client):
        """존재하지 않는 LimitRange 레이블 업데이트"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(LimitRangeUpdateException) as exc_info:
            await lr_manager.update_labels(
                name="test-lr",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, lr_manager, k8s_client, mock_limitrange
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_limit_range = AsyncMock(
            return_value=mock_limitrange
        )
        k8s_client.core_v1.patch_namespaced_limit_range = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(LimitRangeUpdateException) as exc_info:
            await lr_manager.update_labels(
                name="test-lr",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)
