"""ResourceQuotaManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1ResourceQuota,
    V1ObjectMeta,
    V1ResourceQuotaSpec,
    V1ResourceQuotaStatus,
    V1ResourceQuotaList,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra.kubernetes.managers.resourcequota import (
    ResourceQuotaManager,
    ResourceQuotaCreationException,
    ResourceQuotaReadException,
    ResourceQuotaUpdateException,
    ResourceQuotaDeletionException,
    ResourceQuotaListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClientImpl Mock 픽스처"""
    client = MagicMock(spec=KubernetesClientImpl)
    client.core_v1 = AsyncMock()
    return client


@pytest.fixture
def rq_manager(k8s_client):
    """ResourceQuotaManager 픽스처"""
    return ResourceQuotaManager(k8s_client)


@pytest.fixture
def mock_resource_quota():
    """Mock V1ResourceQuota 객체"""
    return V1ResourceQuota(
        api_version="v1",
        kind="ResourceQuota",
        metadata=V1ObjectMeta(
            name="test-quota",
            namespace="test-ns",
            labels={"app_deployment": "test"},
            annotations={"key": "value"},
        ),
        spec=V1ResourceQuotaSpec(
            hard={
                "cpu": "10",
                "memory": "20Gi",
                "pods": "50",
                "services": "10",
            }
        ),
        status=V1ResourceQuotaStatus(
            hard={
                "cpu": "10",
                "memory": "20Gi",
                "pods": "50",
                "services": "10",
            },
            used={
                "cpu": "5",
                "memory": "10Gi",
                "pods": "25",
                "services": "5",
            },
        ),
    )


class TestResourceQuotaManagerInit:
    """ResourceQuotaManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = ResourceQuotaManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = ResourceQuotaManager(k8s_client)
        assert manager.logger is not None


class TestCreateResourceQuota:
    """ResourceQuota 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_resource_quota_success(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """ResourceQuota 생성 성공"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )

        result = await rq_manager.create_resource_quota(
            name="test-quota",
            namespace="test-ns",
            hard_limits={
                "cpu": "10",
                "memory": "20Gi",
                "pods": "50",
                "services": "10",
            },
            labels={"app_deployment": "test"},
            annotations={"key": "value"},
        )

        assert result == mock_resource_quota
        k8s_client.core_v1.create_namespaced_resource_quota.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_resource_quota_already_exists(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """이미 존재하는 ResourceQuota 생성 (멱등성)"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )

        result = await rq_manager.create_resource_quota(
            name="test-quota",
            namespace="test-ns",
            hard_limits={"cpu": "10"},
        )

        assert result == mock_resource_quota
        k8s_client.core_v1.create_namespaced_resource_quota.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_resource_quota_conflict_409(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_resource_quota,  # 재조회: 있음
            ]
        )
        k8s_client.core_v1.create_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await rq_manager.create_resource_quota(
            name="test-quota",
            namespace="test-ns",
            hard_limits={"cpu": "10"},
        )

        assert result == mock_resource_quota
        assert k8s_client.core_v1.read_namespaced_resource_quota.call_count == 2

    @pytest.mark.asyncio
    async def test_create_resource_quota_api_exception(
        self, rq_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ResourceQuotaCreationException) as exc_info:
            await rq_manager.create_resource_quota(
                name="test-quota",
                namespace="test-ns",
                hard_limits={"cpu": "10"},
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_resource_quota_unexpected_exception(
        self, rq_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_resource_quota = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ResourceQuotaCreationException) as exc_info:
            await rq_manager.create_resource_quota(
                name="test-quota",
                namespace="test-ns",
                hard_limits={"cpu": "10"},
            )

        assert "Unexpected error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_resource_quota_with_scopes(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """스코프를 포함한 ResourceQuota 생성"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )

        result = await rq_manager.create_resource_quota(
            name="test-quota",
            namespace="test-ns",
            hard_limits={"cpu": "10"},
            scopes=["BestEffort", "NotTerminating"],
        )

        assert result == mock_resource_quota


class TestGetResourceQuota:
    """ResourceQuota 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_resource_quota_success(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """ResourceQuota 조회 성공"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )

        result = await rq_manager.get_resource_quota(
            name="test-quota",
            namespace="test-ns",
        )

        assert result == mock_resource_quota

    @pytest.mark.asyncio
    async def test_get_resource_quota_not_found(
        self, rq_manager, k8s_client
    ):
        """존재하지 않는 ResourceQuota 조회 (404)"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rq_manager.get_resource_quota(
            name="test-quota",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_resource_quota_api_exception(
        self, rq_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ResourceQuotaReadException) as exc_info:
            await rq_manager.get_resource_quota(
                name="test-quota",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_resource_quota_unexpected_exception(
        self, rq_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ResourceQuotaReadException) as exc_info:
            await rq_manager.get_resource_quota(
                name="test-quota",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteResourceQuota:
    """ResourceQuota 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_resource_quota_success(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """ResourceQuota 삭제 성공"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.delete_namespaced_resource_quota = AsyncMock()

        result = await rq_manager.delete_resource_quota(
            name="test-quota",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_resource_quota.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_resource_quota_not_exists(
        self, rq_manager, k8s_client
    ):
        """존재하지 않는 ResourceQuota 삭제"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ResourceQuotaDeletionException) as exc_info:
            await rq_manager.delete_resource_quota(
                name="test-quota",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_resource_quota_already_deleted_404(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.delete_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rq_manager.delete_resource_quota(
            name="test-quota",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_resource_quota_api_exception(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.delete_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ResourceQuotaDeletionException) as exc_info:
            await rq_manager.delete_resource_quota(
                name="test-quota",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_resource_quota_with_grace_period(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """Grace period 지정 삭제"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.delete_namespaced_resource_quota = AsyncMock()

        result = await rq_manager.delete_resource_quota(
            name="test-quota",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_resource_quota.assert_called_once_with(
            name="test-quota",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListResourceQuotas:
    """ResourceQuota 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_resource_quotas_in_namespace(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """특정 네임스페이스 내 ResourceQuota 목록 조회"""
        mock_list = V1ResourceQuotaList(items=[mock_resource_quota])
        k8s_client.core_v1.list_namespaced_resource_quota = AsyncMock(
            return_value=mock_list
        )

        result = await rq_manager.list_resource_quotas(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_resource_quota

    @pytest.mark.asyncio
    async def test_list_resource_quotas_all_namespaces(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """전체 네임스페이스 ResourceQuota 목록 조회"""
        mock_list = V1ResourceQuotaList(items=[mock_resource_quota])
        k8s_client.core_v1.list_resource_quota_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await rq_manager.list_resource_quotas()

        assert len(result) == 1
        assert result[0] == mock_resource_quota

    @pytest.mark.asyncio
    async def test_list_resource_quotas_with_selectors(
        self, rq_manager, k8s_client
    ):
        """셀렉터를 사용한 ResourceQuota 목록 조회"""
        mock_list = V1ResourceQuotaList(items=[])
        k8s_client.core_v1.list_namespaced_resource_quota = AsyncMock(
            return_value=mock_list
        )

        result = await rq_manager.list_resource_quotas(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-quota",
        )

        assert len(result) == 0
        k8s_client.core_v1.list_namespaced_resource_quota.assert_called_once_with(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-quota",
        )

    @pytest.mark.asyncio
    async def test_list_resource_quotas_api_exception(
        self, rq_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.list_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ResourceQuotaListException) as exc_info:
            await rq_manager.list_resource_quotas(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """ResourceQuota 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """ResourceQuota 존재함"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )

        result = await rq_manager.exists(name="test-quota", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, rq_manager, k8s_client):
        """ResourceQuota 존재하지 않음"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rq_manager.exists(name="test-quota", namespace="test-ns")

        assert result is False


class TestUpdateResourceQuota:
    """ResourceQuota 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_resource_quota_success(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """ResourceQuota 리소스 제한 업데이트 성공"""
        updated_quota = V1ResourceQuota(
            metadata=V1ObjectMeta(
                name="test-quota",
                namespace="test-ns",
            ),
            spec=V1ResourceQuotaSpec(
                hard={
                    "cpu": "20",
                    "memory": "40Gi",
                    "pods": "100",
                }
            ),
        )

        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.patch_namespaced_resource_quota = AsyncMock(
            return_value=updated_quota
        )

        result = await rq_manager.update_resource_quota(
            name="test-quota",
            namespace="test-ns",
            hard_limits={
                "cpu": "20",
                "memory": "40Gi",
                "pods": "100",
            },
        )

        assert result == updated_quota
        k8s_client.core_v1.patch_namespaced_resource_quota.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_resource_quota_not_found(self, rq_manager, k8s_client):
        """존재하지 않는 ResourceQuota 업데이트"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ResourceQuotaUpdateException) as exc_info:
            await rq_manager.update_resource_quota(
                name="test-quota",
                namespace="test-ns",
                hard_limits={"cpu": "20"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_resource_quota_api_exception(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.patch_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ResourceQuotaUpdateException) as exc_info:
            await rq_manager.update_resource_quota(
                name="test-quota",
                namespace="test-ns",
                hard_limits={"cpu": "20"},
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_resource_quota_with_scopes(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """스코프 포함 업데이트"""
        updated_quota = V1ResourceQuota(
            metadata=V1ObjectMeta(name="test-quota", namespace="test-ns"),
            spec=V1ResourceQuotaSpec(
                hard={"cpu": "20"},
                scopes=["BestEffort"],
            ),
        )

        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.patch_namespaced_resource_quota = AsyncMock(
            return_value=updated_quota
        )

        result = await rq_manager.update_resource_quota(
            name="test-quota",
            namespace="test-ns",
            hard_limits={"cpu": "20"},
            scopes=["BestEffort"],
        )

        assert result == updated_quota


class TestGetQuotaStatus:
    """ResourceQuota 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_quota_status_success(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """ResourceQuota 상태 조회 성공"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )

        result = await rq_manager.get_quota_status(
            name="test-quota",
            namespace="test-ns",
        )

        assert result is not None
        assert "hard" in result
        assert "used" in result
        assert result["hard"]["cpu"] == "10"
        assert result["used"]["cpu"] == "5"
        assert result["hard"]["memory"] == "20Gi"
        assert result["used"]["memory"] == "10Gi"

    @pytest.mark.asyncio
    async def test_get_quota_status_not_found(
        self, rq_manager, k8s_client
    ):
        """존재하지 않는 ResourceQuota 상태 조회"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await rq_manager.get_quota_status(
            name="test-quota",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_quota_status_no_status(
        self, rq_manager, k8s_client
    ):
        """상태 정보가 없는 ResourceQuota"""
        quota_without_status = V1ResourceQuota(
            metadata=V1ObjectMeta(name="test-quota", namespace="test-ns"),
            spec=V1ResourceQuotaSpec(hard={"cpu": "10"}),
            status=None,
        )

        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=quota_without_status
        )

        result = await rq_manager.get_quota_status(
            name="test-quota",
            namespace="test-ns",
        )

        assert result is not None
        assert result["hard"] == {"cpu": "10"}
        assert result["used"] == {}


class TestUpdateLabels:
    """ResourceQuota 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """레이블 병합 업데이트"""
        updated_quota = V1ResourceQuota(
            metadata=V1ObjectMeta(
                name="test-quota",
                namespace="test-ns",
                labels={"app_deployment": "test", "env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.patch_namespaced_resource_quota = AsyncMock(
            return_value=updated_quota
        )

        result = await rq_manager.update_labels(
            name="test-quota",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_quota
        k8s_client.core_v1.patch_namespaced_resource_quota.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """레이블 교체 업데이트"""
        updated_quota = V1ResourceQuota(
            metadata=V1ObjectMeta(
                name="test-quota",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.patch_namespaced_resource_quota = AsyncMock(
            return_value=updated_quota
        )

        result = await rq_manager.update_labels(
            name="test-quota",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_quota

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, rq_manager, k8s_client):
        """존재하지 않는 ResourceQuota 레이블 업데이트"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ResourceQuotaUpdateException) as exc_info:
            await rq_manager.update_labels(
                name="test-quota",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, rq_manager, k8s_client, mock_resource_quota
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_resource_quota = AsyncMock(
            return_value=mock_resource_quota
        )
        k8s_client.core_v1.patch_namespaced_resource_quota = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ResourceQuotaUpdateException) as exc_info:
            await rq_manager.update_labels(
                name="test-quota",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)
