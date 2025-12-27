"""ReplicaSetManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1ReplicaSet,
    V1ObjectMeta,
    V1ReplicaSetSpec,
    V1ReplicaSetList,
    V1LabelSelector,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
    V1ReplicaSetStatus,
    V1ReplicaSetCondition,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from infra.kubernetes.managers.replicaset import (
    ReplicaSetManager,
    ReplicaSetCreationException,
    ReplicaSetReadException,
    ReplicaSetUpdateException,
    ReplicaSetDeletionException,
    ReplicaSetListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClient Mock 픽스처"""
    client = MagicMock(spec=KubernetesClient)
    client.apps_v1 = AsyncMock()
    return client


@pytest.fixture
def rs_manager(k8s_client):
    """ReplicaSetManager 픽스처"""
    return ReplicaSetManager(k8s_client)


@pytest.fixture
def mock_container():
    """Mock V1Container 객체"""
    return V1Container(
        name="test-container",
        image="nginx:latest",
        ports=[],
    )


@pytest.fixture
def mock_replicaset(mock_container):
    """Mock V1ReplicaSet 객체"""
    return V1ReplicaSet(
        api_version="apps/v1",
        kind="ReplicaSet",
        metadata=V1ObjectMeta(
            name="test-replicaset",
            namespace="test-ns",
            labels={"app": "test"},
            annotations={"key": "value"},
        ),
        spec=V1ReplicaSetSpec(
            replicas=3,
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
        status=V1ReplicaSetStatus(
            replicas=3,
            ready_replicas=3,
            available_replicas=3,
            fully_labeled_replicas=3,
            conditions=[
                V1ReplicaSetCondition(
                    type="ReplicaFailure",
                    status="False",
                    reason="NoFailure",
                    message="ReplicaSet has no failure.",
                )
            ],
        ),
    )


class TestReplicaSetManagerInit:
    """ReplicaSetManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = ReplicaSetManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = ReplicaSetManager(k8s_client)
        assert manager.logger is not None


class TestCreateReplicaSet:
    """ReplicaSet 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_replicaset_success(
        self, rs_manager, k8s_client, mock_replicaset, mock_container
    ):
        """ReplicaSet 생성 성공"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )

        result = await rs_manager.create_replicaset(
            name="test-replicaset",
            namespace="test-ns",
            containers=[mock_container],
            replicas=3,
            labels={"app": "test"},
            annotations={"key": "value"},
        )

        assert result == mock_replicaset
        k8s_client.apps_v1.create_namespaced_replica_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_replicaset_already_exists(
        self, rs_manager, k8s_client, mock_replicaset, mock_container
    ):
        """이미 존재하는 ReplicaSet 생성 (멱등성)"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )

        result = await rs_manager.create_replicaset(
            name="test-replicaset",
            namespace="test-ns",
            containers=[mock_container],
        )

        assert result == mock_replicaset
        k8s_client.apps_v1.create_namespaced_replica_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_replicaset_conflict_409(
        self, rs_manager, k8s_client, mock_replicaset, mock_container
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_replicaset,  # 재조회: 있음
            ]
        )
        k8s_client.apps_v1.create_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await rs_manager.create_replicaset(
            name="test-replicaset",
            namespace="test-ns",
            containers=[mock_container],
        )

        assert result == mock_replicaset
        assert k8s_client.apps_v1.read_namespaced_replica_set.call_count == 2

    @pytest.mark.asyncio
    async def test_create_replicaset_api_exception(
        self, rs_manager, k8s_client, mock_container
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ReplicaSetCreationException) as exc_info:
            await rs_manager.create_replicaset(
                name="test-replicaset",
                namespace="test-ns",
                containers=[mock_container],
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_replicaset_unexpected_exception(
        self, rs_manager, k8s_client, mock_container
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_replica_set = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ReplicaSetCreationException) as exc_info:
            await rs_manager.create_replicaset(
                name="test-replicaset",
                namespace="test-ns",
                containers=[mock_container],
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetReplicaSet:
    """ReplicaSet 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_replicaset_success(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """ReplicaSet 조회 성공"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )

        result = await rs_manager.get_replicaset(
            name="test-replicaset",
            namespace="test-ns",
        )

        assert result == mock_replicaset

    @pytest.mark.asyncio
    async def test_get_replicaset_not_found(
        self, rs_manager, k8s_client
    ):
        """존재하지 않는 ReplicaSet 조회 (404)"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rs_manager.get_replicaset(
            name="test-replicaset",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_replicaset_api_exception(
        self, rs_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ReplicaSetReadException) as exc_info:
            await rs_manager.get_replicaset(
                name="test-replicaset",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_replicaset_unexpected_exception(
        self, rs_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ReplicaSetReadException) as exc_info:
            await rs_manager.get_replicaset(
                name="test-replicaset",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteReplicaSet:
    """ReplicaSet 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_replicaset_success(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """ReplicaSet 삭제 성공"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )
        k8s_client.apps_v1.delete_namespaced_replica_set = AsyncMock()

        result = await rs_manager.delete_replicaset(
            name="test-replicaset",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.apps_v1.delete_namespaced_replica_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_replicaset_not_exists(
        self, rs_manager, k8s_client
    ):
        """존재하지 않는 ReplicaSet 삭제"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ReplicaSetDeletionException) as exc_info:
            await rs_manager.delete_replicaset(
                name="test-replicaset",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_replicaset_already_deleted_404(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )
        k8s_client.apps_v1.delete_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rs_manager.delete_replicaset(
            name="test-replicaset",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_replicaset_api_exception(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )
        k8s_client.apps_v1.delete_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ReplicaSetDeletionException) as exc_info:
            await rs_manager.delete_replicaset(
                name="test-replicaset",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_replicaset_with_grace_period(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """Grace period 지정 삭제"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )
        k8s_client.apps_v1.delete_namespaced_replica_set = AsyncMock()

        result = await rs_manager.delete_replicaset(
            name="test-replicaset",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.apps_v1.delete_namespaced_replica_set.assert_called_once_with(
            name="test-replicaset",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListReplicaSets:
    """ReplicaSet 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_replicasets_in_namespace(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """특정 네임스페이스 내 ReplicaSet 목록 조회"""
        mock_list = V1ReplicaSetList(items=[mock_replicaset])
        k8s_client.apps_v1.list_namespaced_replica_set = AsyncMock(
            return_value=mock_list
        )

        result = await rs_manager.list_replicasets(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_replicaset

    @pytest.mark.asyncio
    async def test_list_replicasets_all_namespaces(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """전체 네임스페이스 ReplicaSet 목록 조회"""
        mock_list = V1ReplicaSetList(items=[mock_replicaset])
        k8s_client.apps_v1.list_replica_set_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await rs_manager.list_replicasets()

        assert len(result) == 1
        assert result[0] == mock_replicaset

    @pytest.mark.asyncio
    async def test_list_replicasets_with_selectors(
        self, rs_manager, k8s_client
    ):
        """셀렉터를 사용한 ReplicaSet 목록 조회"""
        mock_list = V1ReplicaSetList(items=[])
        k8s_client.apps_v1.list_namespaced_replica_set = AsyncMock(
            return_value=mock_list
        )

        result = await rs_manager.list_replicasets(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-replicaset",
        )

        assert len(result) == 0
        k8s_client.apps_v1.list_namespaced_replica_set.assert_called_once_with(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-replicaset",
        )

    @pytest.mark.asyncio
    async def test_list_replicasets_api_exception(
        self, rs_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.list_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ReplicaSetListException) as exc_info:
            await rs_manager.list_replicasets(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """ReplicaSet 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """ReplicaSet 존재함"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )

        result = await rs_manager.exists(name="test-replicaset", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, rs_manager, k8s_client):
        """ReplicaSet 존재하지 않음"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rs_manager.exists(name="test-replicaset", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """ReplicaSet 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """레이블 병합 업데이트"""
        updated_rs = V1ReplicaSet(
            metadata=V1ObjectMeta(
                name="test-replicaset",
                namespace="test-ns",
                labels={"app": "test", "env": "prod"},
            )
        )

        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )
        k8s_client.apps_v1.patch_namespaced_replica_set = AsyncMock(
            return_value=updated_rs
        )

        result = await rs_manager.update_labels(
            name="test-replicaset",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_rs
        k8s_client.apps_v1.patch_namespaced_replica_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """레이블 교체 업데이트"""
        updated_rs = V1ReplicaSet(
            metadata=V1ObjectMeta(
                name="test-replicaset",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )
        k8s_client.apps_v1.patch_namespaced_replica_set = AsyncMock(
            return_value=updated_rs
        )

        result = await rs_manager.update_labels(
            name="test-replicaset",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_rs

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, rs_manager, k8s_client):
        """존재하지 않는 ReplicaSet 레이블 업데이트"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ReplicaSetUpdateException) as exc_info:
            await rs_manager.update_labels(
                name="test-replicaset",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )
        k8s_client.apps_v1.patch_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ReplicaSetUpdateException) as exc_info:
            await rs_manager.update_labels(
                name="test-replicaset",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestUpdateReplicas:
    """ReplicaSet 레플리카 수 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_replicas_success(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """레플리카 수 업데이트 성공"""
        updated_rs = V1ReplicaSet(
            metadata=V1ObjectMeta(
                name="test-replicaset",
                namespace="test-ns",
            ),
            spec=V1ReplicaSetSpec(
                replicas=5,
                selector=V1LabelSelector(match_labels={"app": "test"}),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": "test"}),
                    spec=V1PodSpec(containers=[]),
                ),
            ),
        )

        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )
        k8s_client.apps_v1.patch_namespaced_replica_set = AsyncMock(
            return_value=updated_rs
        )

        result = await rs_manager.update_replicas(
            name="test-replicaset",
            namespace="test-ns",
            replicas=5,
        )

        assert result == updated_rs
        k8s_client.apps_v1.patch_namespaced_replica_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_replicas_not_found(self, rs_manager, k8s_client):
        """존재하지 않는 ReplicaSet 레플리카 수 업데이트"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ReplicaSetUpdateException) as exc_info:
            await rs_manager.update_replicas(
                name="test-replicaset",
                namespace="test-ns",
                replicas=5,
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_replicas_api_exception(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )
        k8s_client.apps_v1.patch_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ReplicaSetUpdateException) as exc_info:
            await rs_manager.update_replicas(
                name="test-replicaset",
                namespace="test-ns",
                replicas=5,
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestGetReplicaSetStatus:
    """ReplicaSet 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_replicaset_status_success(
        self, rs_manager, k8s_client, mock_replicaset
    ):
        """ReplicaSet 상태 조회 성공"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=mock_replicaset
        )

        result = await rs_manager.get_replicaset_status(
            name="test-replicaset",
            namespace="test-ns",
        )

        assert result is not None
        assert result["replicas"] == 3
        assert result["ready_replicas"] == 3
        assert result["available_replicas"] == 3
        assert result["fully_labeled_replicas"] == 3
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "ReplicaFailure"

    @pytest.mark.asyncio
    async def test_get_replicaset_status_not_found(
        self, rs_manager, k8s_client
    ):
        """존재하지 않는 ReplicaSet 상태 조회"""
        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rs_manager.get_replicaset_status(
            name="test-replicaset",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_replicaset_status_no_status(
        self, rs_manager, k8s_client
    ):
        """Status가 없는 ReplicaSet"""
        replicaset_no_status = V1ReplicaSet(
            metadata=V1ObjectMeta(
                name="test-replicaset",
                namespace="test-ns",
            ),
            spec=V1ReplicaSetSpec(
                replicas=1,
                selector=V1LabelSelector(match_labels={"app": "test"}),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": "test"}),
                    spec=V1PodSpec(containers=[]),
                ),
            ),
        )

        k8s_client.apps_v1.read_namespaced_replica_set = AsyncMock(
            return_value=replicaset_no_status
        )

        result = await rs_manager.get_replicaset_status(
            name="test-replicaset",
            namespace="test-ns",
        )

        assert result is None
