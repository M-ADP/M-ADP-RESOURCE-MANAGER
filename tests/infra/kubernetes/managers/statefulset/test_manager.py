"""StatefulSetManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1StatefulSet,
    V1ObjectMeta,
    V1StatefulSetSpec,
    V1StatefulSetStatus,
    V1LabelSelector,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
    V1StatefulSetList,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from infra.kubernetes.managers.statefulset import (
    StatefulSetManager,
    StatefulSetCreationException,
    StatefulSetReadException,
    StatefulSetUpdateException,
    StatefulSetDeletionException,
    StatefulSetListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClient Mock 픽스처"""
    client = MagicMock(spec=KubernetesClient)
    client.apps_v1 = AsyncMock()
    return client


@pytest.fixture
def sts_manager(k8s_client):
    """StatefulSetManager 픽스처"""
    return StatefulSetManager(k8s_client)


@pytest.fixture
def mock_statefulset():
    """Mock V1StatefulSet 객체"""
    return V1StatefulSet(
        api_version="apps/v1",
        kind="StatefulSet",
        metadata=V1ObjectMeta(
            name="test-sts",
            namespace="test-ns",
            labels={"app": "test"},
            annotations={"key": "value"},
        ),
        spec=V1StatefulSetSpec(
            service_name="test-service",
            replicas=3,
            selector=V1LabelSelector(match_labels={"app": "test"}),
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels={"app": "test"}),
                spec=V1PodSpec(
                    containers=[
                        V1Container(
                            name="test-container",
                            image="test:latest",
                        )
                    ]
                ),
            ),
        ),
        status=V1StatefulSetStatus(
            replicas=3,
            ready_replicas=3,
            current_replicas=3,
            updated_replicas=3,
        ),
    )


class TestStatefulSetManagerInit:
    """StatefulSetManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = StatefulSetManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = StatefulSetManager(k8s_client)
        assert manager.logger is not None


class TestCreateStatefulSet:
    """StatefulSet 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_statefulset_success(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """StatefulSet 생성 성공"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )

        container = V1Container(name="test-container", image="test:latest")
        result = await sts_manager.create_statefulset(
            name="test-sts",
            namespace="test-ns",
            service_name="test-service",
            replicas=3,
            selector={"app": "test"},
            containers=[container],
            labels={"app": "test"},
        )

        assert result == mock_statefulset
        k8s_client.apps_v1.create_namespaced_stateful_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_statefulset_already_exists(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """이미 존재하는 StatefulSet 생성 (멱등성)"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )

        container = V1Container(name="test-container", image="test:latest")
        result = await sts_manager.create_statefulset(
            name="test-sts",
            namespace="test-ns",
            service_name="test-service",
            replicas=3,
            selector={"app": "test"},
            containers=[container],
        )

        assert result == mock_statefulset
        k8s_client.apps_v1.create_namespaced_stateful_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_statefulset_conflict_409(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_statefulset,  # 재조회: 있음
            ]
        )
        k8s_client.apps_v1.create_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        container = V1Container(name="test-container", image="test:latest")
        result = await sts_manager.create_statefulset(
            name="test-sts",
            namespace="test-ns",
            service_name="test-service",
            replicas=3,
            selector={"app": "test"},
            containers=[container],
        )

        assert result == mock_statefulset
        assert k8s_client.apps_v1.read_namespaced_stateful_set.call_count == 2

    @pytest.mark.asyncio
    async def test_create_statefulset_api_exception(
        self, sts_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        container = V1Container(name="test-container", image="test:latest")
        with pytest.raises(StatefulSetCreationException) as exc_info:
            await sts_manager.create_statefulset(
                name="test-sts",
                namespace="test-ns",
                service_name="test-service",
                replicas=3,
                selector={"app": "test"},
                containers=[container],
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_statefulset_unexpected_exception(
        self, sts_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_stateful_set = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        container = V1Container(name="test-container", image="test:latest")
        with pytest.raises(StatefulSetCreationException) as exc_info:
            await sts_manager.create_statefulset(
                name="test-sts",
                namespace="test-ns",
                service_name="test-service",
                replicas=3,
                selector={"app": "test"},
                containers=[container],
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetStatefulSet:
    """StatefulSet 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_statefulset_success(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """StatefulSet 조회 성공"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )

        result = await sts_manager.get_statefulset(
            name="test-sts",
            namespace="test-ns",
        )

        assert result == mock_statefulset

    @pytest.mark.asyncio
    async def test_get_statefulset_not_found(
        self, sts_manager, k8s_client
    ):
        """존재하지 않는 StatefulSet 조회 (404)"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await sts_manager.get_statefulset(
            name="test-sts",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_statefulset_api_exception(
        self, sts_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(StatefulSetReadException) as exc_info:
            await sts_manager.get_statefulset(
                name="test-sts",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_statefulset_unexpected_exception(
        self, sts_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(StatefulSetReadException) as exc_info:
            await sts_manager.get_statefulset(
                name="test-sts",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteStatefulSet:
    """StatefulSet 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_statefulset_success(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """StatefulSet 삭제 성공"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.delete_namespaced_stateful_set = AsyncMock()

        result = await sts_manager.delete_statefulset(
            name="test-sts",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.apps_v1.delete_namespaced_stateful_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_statefulset_not_exists(
        self, sts_manager, k8s_client
    ):
        """존재하지 않는 StatefulSet 삭제 (멱등성)"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await sts_manager.delete_statefulset(
            name="test-sts",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.apps_v1.delete_namespaced_stateful_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_statefulset_already_deleted_404(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.delete_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await sts_manager.delete_statefulset(
            name="test-sts",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_statefulset_api_exception(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.delete_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(StatefulSetDeletionException) as exc_info:
            await sts_manager.delete_statefulset(
                name="test-sts",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_statefulset_with_grace_period(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """Grace period 지정 삭제"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.delete_namespaced_stateful_set = AsyncMock()

        result = await sts_manager.delete_statefulset(
            name="test-sts",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.apps_v1.delete_namespaced_stateful_set.assert_called_once_with(
            name="test-sts",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListStatefulSets:
    """StatefulSet 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_statefulsets_in_namespace(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """특정 네임스페이스 내 StatefulSet 목록 조회"""
        mock_list = V1StatefulSetList(items=[mock_statefulset])
        k8s_client.apps_v1.list_namespaced_stateful_set = AsyncMock(
            return_value=mock_list
        )

        result = await sts_manager.list_statefulsets(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_statefulset

    @pytest.mark.asyncio
    async def test_list_statefulsets_all_namespaces(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """전체 네임스페이스 StatefulSet 목록 조회"""
        mock_list = V1StatefulSetList(items=[mock_statefulset])
        k8s_client.apps_v1.list_stateful_set_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await sts_manager.list_statefulsets()

        assert len(result) == 1
        assert result[0] == mock_statefulset

    @pytest.mark.asyncio
    async def test_list_statefulsets_with_selectors(
        self, sts_manager, k8s_client
    ):
        """셀렉터를 사용한 StatefulSet 목록 조회"""
        mock_list = V1StatefulSetList(items=[])
        k8s_client.apps_v1.list_namespaced_stateful_set = AsyncMock(
            return_value=mock_list
        )

        result = await sts_manager.list_statefulsets(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-sts",
        )

        assert len(result) == 0
        k8s_client.apps_v1.list_namespaced_stateful_set.assert_called_once_with(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-sts",
        )

    @pytest.mark.asyncio
    async def test_list_statefulsets_api_exception(
        self, sts_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.list_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(StatefulSetListException) as exc_info:
            await sts_manager.list_statefulsets(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """StatefulSet 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """StatefulSet 존재함"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )

        result = await sts_manager.exists(name="test-sts", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, sts_manager, k8s_client):
        """StatefulSet 존재하지 않음"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await sts_manager.exists(name="test-sts", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """StatefulSet 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """레이블 병합 업데이트"""
        updated_sts = V1StatefulSet(
            metadata=V1ObjectMeta(
                name="test-sts",
                namespace="test-ns",
                labels={"app": "test", "env": "prod"},
            )
        )

        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.patch_namespaced_stateful_set = AsyncMock(
            return_value=updated_sts
        )

        result = await sts_manager.update_labels(
            name="test-sts",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_sts
        k8s_client.apps_v1.patch_namespaced_stateful_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """레이블 교체 업데이트"""
        updated_sts = V1StatefulSet(
            metadata=V1ObjectMeta(
                name="test-sts",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.patch_namespaced_stateful_set = AsyncMock(
            return_value=updated_sts
        )

        result = await sts_manager.update_labels(
            name="test-sts",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_sts

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, sts_manager, k8s_client):
        """존재하지 않는 StatefulSet 레이블 업데이트"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(StatefulSetUpdateException) as exc_info:
            await sts_manager.update_labels(
                name="test-sts",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.patch_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(StatefulSetUpdateException) as exc_info:
            await sts_manager.update_labels(
                name="test-sts",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestUpdateAnnotations:
    """StatefulSet 어노테이션 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_annotations_merge(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """어노테이션 병합 업데이트"""
        updated_sts = V1StatefulSet(
            metadata=V1ObjectMeta(
                name="test-sts",
                namespace="test-ns",
                annotations={"key": "value", "new-key": "new-value"},
            )
        )

        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.patch_namespaced_stateful_set = AsyncMock(
            return_value=updated_sts
        )

        result = await sts_manager.update_annotations(
            name="test-sts",
            namespace="test-ns",
            annotations={"new-key": "new-value"},
            merge=True,
        )

        assert result == updated_sts

    @pytest.mark.asyncio
    async def test_update_annotations_replace(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """어노테이션 교체 업데이트"""
        updated_sts = V1StatefulSet(
            metadata=V1ObjectMeta(
                name="test-sts",
                namespace="test-ns",
                annotations={"new-key": "new-value"},
            )
        )

        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.patch_namespaced_stateful_set = AsyncMock(
            return_value=updated_sts
        )

        result = await sts_manager.update_annotations(
            name="test-sts",
            namespace="test-ns",
            annotations={"new-key": "new-value"},
            merge=False,
        )

        assert result == updated_sts

    @pytest.mark.asyncio
    async def test_update_annotations_not_found(self, sts_manager, k8s_client):
        """존재하지 않는 StatefulSet 어노테이션 업데이트"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(StatefulSetUpdateException) as exc_info:
            await sts_manager.update_annotations(
                name="test-sts",
                namespace="test-ns",
                annotations={"key": "value"},
            )

        assert "does not exist" in str(exc_info.value)


class TestScaleStatefulSet:
    """StatefulSet 스케일 조정 테스트"""

    @pytest.mark.asyncio
    async def test_scale_statefulset_success(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """StatefulSet 스케일 조정 성공"""
        updated_sts = V1StatefulSet(
            metadata=V1ObjectMeta(name="test-sts", namespace="test-ns"),
            spec=V1StatefulSetSpec(
                replicas=5,
                selector=V1LabelSelector(match_labels={"app": "test"}),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": "test"}),
                    spec=V1PodSpec(containers=[]),
                ),
            ),
        )

        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.patch_namespaced_stateful_set = AsyncMock(
            return_value=updated_sts
        )

        result = await sts_manager.scale_statefulset(
            name="test-sts",
            namespace="test-ns",
            replicas=5,
        )

        assert result == updated_sts

    @pytest.mark.asyncio
    async def test_scale_statefulset_not_found(self, sts_manager, k8s_client):
        """존재하지 않는 StatefulSet 스케일 조정"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(StatefulSetUpdateException) as exc_info:
            await sts_manager.scale_statefulset(
                name="test-sts",
                namespace="test-ns",
                replicas=5,
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_scale_statefulset_api_exception(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )
        k8s_client.apps_v1.patch_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(StatefulSetUpdateException) as exc_info:
            await sts_manager.scale_statefulset(
                name="test-sts",
                namespace="test-ns",
                replicas=5,
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestGetStatefulSetStatus:
    """StatefulSet 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_statefulset_status_success(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """StatefulSet 상태 조회 성공"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )

        result = await sts_manager.get_statefulset_status(
            name="test-sts",
            namespace="test-ns",
        )

        assert result is not None
        assert result["replicas"] == 3
        assert result["ready_replicas"] == 3

    @pytest.mark.asyncio
    async def test_get_statefulset_status_not_found(
        self, sts_manager, k8s_client
    ):
        """존재하지 않는 StatefulSet 상태 조회"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await sts_manager.get_statefulset_status(
            name="test-sts",
            namespace="test-ns",
        )

        assert result is None


class TestIsReady:
    """StatefulSet 준비 상태 확인 테스트"""

    @pytest.mark.asyncio
    async def test_is_ready_true(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """StatefulSet 준비 완료"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )

        result = await sts_manager.is_ready(name="test-sts", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_ready_false(
        self, sts_manager, k8s_client, mock_statefulset
    ):
        """StatefulSet 준비 미완료"""
        # ready_replicas가 replicas보다 적음
        mock_statefulset.status.ready_replicas = 1

        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            return_value=mock_statefulset
        )

        result = await sts_manager.is_ready(name="test-sts", namespace="test-ns")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_ready_not_found(self, sts_manager, k8s_client):
        """존재하지 않는 StatefulSet 준비 상태 확인"""
        k8s_client.apps_v1.read_namespaced_stateful_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await sts_manager.is_ready(name="test-sts", namespace="test-ns")

        assert result is False
