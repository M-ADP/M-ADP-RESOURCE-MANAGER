"""ConfigMapManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1ConfigMap,
    V1ObjectMeta,
    V1ConfigMapList,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from infra.kubernetes.managers.configmap import (
    ConfigMapManager,
    ConfigMapCreationException,
    ConfigMapReadException,
    ConfigMapUpdateException,
    ConfigMapDeletionException,
    ConfigMapListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClient Mock 픽스처"""
    client = MagicMock(spec=KubernetesClient)
    client.core_v1 = AsyncMock()
    return client


@pytest.fixture
def cm_manager(k8s_client):
    """ConfigMapManager 픽스처"""
    return ConfigMapManager(k8s_client)


@pytest.fixture
def mock_configmap():
    """Mock V1ConfigMap 객체"""
    return V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=V1ObjectMeta(
            name="test-cm",
            namespace="test-ns",
            labels={"app": "test"},
            annotations={"key": "value"},
        ),
        data={"config.yaml": "key: value", "setting": "enabled"},
    )


class TestConfigMapManagerInit:
    """ConfigMapManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = ConfigMapManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = ConfigMapManager(k8s_client)
        assert manager.logger is not None


class TestCreateConfigMap:
    """ConfigMap 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_configmap_success(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """ConfigMap 생성 성공"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )

        result = await cm_manager.create_configmap(
            name="test-cm",
            namespace="test-ns",
            data={"config.yaml": "key: value", "setting": "enabled"},
            labels={"app": "test"},
            annotations={"key": "value"},
        )

        assert result == mock_configmap
        k8s_client.core_v1.create_namespaced_config_map.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_configmap_already_exists(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """이미 존재하는 ConfigMap 생성 (멱등성)"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )

        result = await cm_manager.create_configmap(
            name="test-cm",
            namespace="test-ns",
        )

        assert result == mock_configmap
        k8s_client.core_v1.create_namespaced_config_map.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_configmap_conflict_409(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_configmap,  # 재조회: 있음
            ]
        )
        k8s_client.core_v1.create_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await cm_manager.create_configmap(
            name="test-cm",
            namespace="test-ns",
        )

        assert result == mock_configmap
        assert k8s_client.core_v1.read_namespaced_config_map.call_count == 2

    @pytest.mark.asyncio
    async def test_create_configmap_api_exception(
        self, cm_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ConfigMapCreationException) as exc_info:
            await cm_manager.create_configmap(
                name="test-cm",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_configmap_unexpected_exception(
        self, cm_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_config_map = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ConfigMapCreationException) as exc_info:
            await cm_manager.create_configmap(
                name="test-cm",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetConfigMap:
    """ConfigMap 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_configmap_success(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """ConfigMap 조회 성공"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )

        result = await cm_manager.get_configmap(
            name="test-cm",
            namespace="test-ns",
        )

        assert result == mock_configmap

    @pytest.mark.asyncio
    async def test_get_configmap_not_found(
        self, cm_manager, k8s_client
    ):
        """존재하지 않는 ConfigMap 조회 (404)"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await cm_manager.get_configmap(
            name="test-cm",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_configmap_api_exception(
        self, cm_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ConfigMapReadException) as exc_info:
            await cm_manager.get_configmap(
                name="test-cm",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_configmap_unexpected_exception(
        self, cm_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ConfigMapReadException) as exc_info:
            await cm_manager.get_configmap(
                name="test-cm",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteConfigMap:
    """ConfigMap 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_configmap_success(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """ConfigMap 삭제 성공"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.delete_namespaced_config_map = AsyncMock()

        result = await cm_manager.delete_configmap(
            name="test-cm",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_config_map.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_configmap_not_exists(
        self, cm_manager, k8s_client
    ):
        """존재하지 않는 ConfigMap 삭제"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ConfigMapDeletionException) as exc_info:
            await cm_manager.delete_configmap(
                name="test-cm",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_configmap_already_deleted_404(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.delete_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await cm_manager.delete_configmap(
            name="test-cm",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_configmap_api_exception(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.delete_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ConfigMapDeletionException) as exc_info:
            await cm_manager.delete_configmap(
                name="test-cm",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_configmap_with_grace_period(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """Grace period 지정 삭제"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.delete_namespaced_config_map = AsyncMock()

        result = await cm_manager.delete_configmap(
            name="test-cm",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_config_map.assert_called_once_with(
            name="test-cm",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListConfigMaps:
    """ConfigMap 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_configmaps_in_namespace(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """특정 네임스페이스 내 ConfigMap 목록 조회"""
        mock_list = V1ConfigMapList(items=[mock_configmap])
        k8s_client.core_v1.list_namespaced_config_map = AsyncMock(
            return_value=mock_list
        )

        result = await cm_manager.list_configmaps(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_configmap

    @pytest.mark.asyncio
    async def test_list_configmaps_all_namespaces(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """전체 네임스페이스 ConfigMap 목록 조회"""
        mock_list = V1ConfigMapList(items=[mock_configmap])
        k8s_client.core_v1.list_config_map_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await cm_manager.list_configmaps()

        assert len(result) == 1
        assert result[0] == mock_configmap

    @pytest.mark.asyncio
    async def test_list_configmaps_with_selectors(
        self, cm_manager, k8s_client
    ):
        """셀렉터를 사용한 ConfigMap 목록 조회"""
        mock_list = V1ConfigMapList(items=[])
        k8s_client.core_v1.list_namespaced_config_map = AsyncMock(
            return_value=mock_list
        )

        result = await cm_manager.list_configmaps(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-cm",
        )

        assert len(result) == 0
        k8s_client.core_v1.list_namespaced_config_map.assert_called_once_with(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-cm",
        )

    @pytest.mark.asyncio
    async def test_list_configmaps_api_exception(
        self, cm_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.list_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ConfigMapListException) as exc_info:
            await cm_manager.list_configmaps(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """ConfigMap 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """ConfigMap 존재함"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )

        result = await cm_manager.exists(name="test-cm", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, cm_manager, k8s_client):
        """ConfigMap 존재하지 않음"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await cm_manager.exists(name="test-cm", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """ConfigMap 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """레이블 병합 업데이트"""
        updated_cm = V1ConfigMap(
            metadata=V1ObjectMeta(
                name="test-cm",
                namespace="test-ns",
                labels={"app": "test", "env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.patch_namespaced_config_map = AsyncMock(
            return_value=updated_cm
        )

        result = await cm_manager.update_labels(
            name="test-cm",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_cm
        k8s_client.core_v1.patch_namespaced_config_map.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """레이블 교체 업데이트"""
        updated_cm = V1ConfigMap(
            metadata=V1ObjectMeta(
                name="test-cm",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.patch_namespaced_config_map = AsyncMock(
            return_value=updated_cm
        )

        result = await cm_manager.update_labels(
            name="test-cm",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_cm

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, cm_manager, k8s_client):
        """존재하지 않는 ConfigMap 레이블 업데이트"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ConfigMapUpdateException) as exc_info:
            await cm_manager.update_labels(
                name="test-cm",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.patch_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ConfigMapUpdateException) as exc_info:
            await cm_manager.update_labels(
                name="test-cm",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestUpdateData:
    """ConfigMap 데이터 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_data_merge(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """데이터 병합 업데이트"""
        updated_cm = V1ConfigMap(
            metadata=V1ObjectMeta(name="test-cm", namespace="test-ns"),
            data={
                "config.yaml": "key: value",
                "setting": "enabled",
                "new-key": "new-value",
            },
        )

        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.patch_namespaced_config_map = AsyncMock(
            return_value=updated_cm
        )

        result = await cm_manager.update_data(
            name="test-cm",
            namespace="test-ns",
            data={"new-key": "new-value"},
            merge=True,
        )

        assert result == updated_cm
        k8s_client.core_v1.patch_namespaced_config_map.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_data_replace(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """데이터 교체 업데이트"""
        updated_cm = V1ConfigMap(
            metadata=V1ObjectMeta(name="test-cm", namespace="test-ns"),
            data={"new-key": "new-value"},
        )

        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.patch_namespaced_config_map = AsyncMock(
            return_value=updated_cm
        )

        result = await cm_manager.update_data(
            name="test-cm",
            namespace="test-ns",
            data={"new-key": "new-value"},
            merge=False,
        )

        assert result == updated_cm

    @pytest.mark.asyncio
    async def test_update_data_not_found(self, cm_manager, k8s_client):
        """존재하지 않는 ConfigMap 데이터 업데이트"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ConfigMapUpdateException) as exc_info:
            await cm_manager.update_data(
                name="test-cm",
                namespace="test-ns",
                data={"key": "value"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_data_api_exception(
        self, cm_manager, k8s_client, mock_configmap
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_config_map = AsyncMock(
            return_value=mock_configmap
        )
        k8s_client.core_v1.patch_namespaced_config_map = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ConfigMapUpdateException) as exc_info:
            await cm_manager.update_data(
                name="test-cm",
                namespace="test-ns",
                data={"key": "value"},
            )

        assert "Internal Server Error" in str(exc_info.value)
