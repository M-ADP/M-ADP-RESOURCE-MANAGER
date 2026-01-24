"""PersistentVolumeClaimManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1PersistentVolumeClaim,
    V1ObjectMeta,
    V1PersistentVolumeClaimSpec,
    V1PersistentVolumeClaimList,
    V1ResourceRequirements,
    V1PersistentVolumeClaimStatus,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra.kubernetes.managers.persistentvolumeclaim import (
    PersistentVolumeClaimManager,
    PersistentVolumeClaimCreationException,
    PersistentVolumeClaimReadException,
    PersistentVolumeClaimUpdateException,
    PersistentVolumeClaimDeletionException,
    PersistentVolumeClaimListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClientImpl Mock 픽스처"""
    client = MagicMock(spec=KubernetesClientImpl)
    client.core_v1 = AsyncMock()
    return client


@pytest.fixture
def pvc_manager(k8s_client):
    """PersistentVolumeClaimManager 픽스처"""
    return PersistentVolumeClaimManager(k8s_client)


@pytest.fixture
def mock_pvc():
    """Mock V1PersistentVolumeClaim 객체"""
    return V1PersistentVolumeClaim(
        api_version="v1",
        kind="PersistentVolumeClaim",
        metadata=V1ObjectMeta(
            name="test-pvc",
            namespace="test-ns",
            labels={"app": "test"},
            annotations={"key": "value"},
        ),
        spec=V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=V1ResourceRequirements(
                requests={"storage": "10Gi"}
            ),
            storage_class_name="standard",
        ),
        status=V1PersistentVolumeClaimStatus(
            phase="Bound",
            access_modes=["ReadWriteOnce"],
            capacity={"storage": "10Gi"},
            conditions=[],
        ),
    )


class TestPVCManagerInit:
    """PersistentVolumeClaimManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = PersistentVolumeClaimManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = PersistentVolumeClaimManager(k8s_client)
        assert manager.logger is not None


class TestCreatePVC:
    """PVC 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_pvc_success(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """PVC 생성 성공"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )

        result = await pvc_manager.create_pvc(
            name="test-pvc",
            namespace="test-ns",
            storage_size="10Gi",
            access_modes=["ReadWriteOnce"],
            storage_class_name="standard",
            labels={"app": "test"},
            annotations={"key": "value"},
        )

        assert result == mock_pvc
        k8s_client.core_v1.create_namespaced_persistent_volume_claim.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_pvc_already_exists(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """이미 존재하는 PVC 생성 (멱등성)"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )

        result = await pvc_manager.create_pvc(
            name="test-pvc",
            namespace="test-ns",
            storage_size="10Gi",
        )

        assert result == mock_pvc
        k8s_client.core_v1.create_namespaced_persistent_volume_claim.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_pvc_conflict_409(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_pvc,  # 재조회: 있음
            ]
        )
        k8s_client.core_v1.create_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await pvc_manager.create_pvc(
            name="test-pvc",
            namespace="test-ns",
            storage_size="10Gi",
        )

        assert result == mock_pvc
        assert k8s_client.core_v1.read_namespaced_persistent_volume_claim.call_count == 2

    @pytest.mark.asyncio
    async def test_create_pvc_api_exception(
        self, pvc_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(PersistentVolumeClaimCreationException) as exc_info:
            await pvc_manager.create_pvc(
                name="test-pvc",
                namespace="test-ns",
                storage_size="10Gi",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_pvc_with_default_access_modes(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """기본 access_modes로 PVC 생성"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )

        result = await pvc_manager.create_pvc(
            name="test-pvc",
            namespace="test-ns",
            storage_size="10Gi",
        )

        assert result == mock_pvc


class TestGetPVC:
    """PVC 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_pvc_success(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """PVC 조회 성공"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )

        result = await pvc_manager.get_pvc(
            name="test-pvc",
            namespace="test-ns",
        )

        assert result == mock_pvc

    @pytest.mark.asyncio
    async def test_get_pvc_not_found(
        self, pvc_manager, k8s_client
    ):
        """존재하지 않는 PVC 조회 (404)"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await pvc_manager.get_pvc(
            name="test-pvc",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_pvc_api_exception(
        self, pvc_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(PersistentVolumeClaimReadException) as exc_info:
            await pvc_manager.get_pvc(
                name="test-pvc",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestDeletePVC:
    """PVC 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_pvc_success(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """PVC 삭제 성공"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )
        k8s_client.core_v1.delete_namespaced_persistent_volume_claim = AsyncMock()

        result = await pvc_manager.delete_pvc(
            name="test-pvc",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_persistent_volume_claim.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_pvc_not_exists(
        self, pvc_manager, k8s_client
    ):
        """존재하지 않는 PVC 삭제"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(PersistentVolumeClaimDeletionException) as exc_info:
            await pvc_manager.delete_pvc(
                name="test-pvc",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_pvc_already_deleted_404(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )
        k8s_client.core_v1.delete_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await pvc_manager.delete_pvc(
            name="test-pvc",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_pvc_with_grace_period(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """Grace period 지정 삭제"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )
        k8s_client.core_v1.delete_namespaced_persistent_volume_claim = AsyncMock()

        result = await pvc_manager.delete_pvc(
            name="test-pvc",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_persistent_volume_claim.assert_called_once_with(
            name="test-pvc",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListPVCs:
    """PVC 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_pvcs_in_namespace(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """특정 네임스페이스 내 PVC 목록 조회"""
        mock_list = V1PersistentVolumeClaimList(items=[mock_pvc])
        k8s_client.core_v1.list_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_list
        )

        result = await pvc_manager.list_pvcs(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_pvc

    @pytest.mark.asyncio
    async def test_list_pvcs_all_namespaces(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """전체 네임스페이스 PVC 목록 조회"""
        mock_list = V1PersistentVolumeClaimList(items=[mock_pvc])
        k8s_client.core_v1.list_persistent_volume_claim_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await pvc_manager.list_pvcs()

        assert len(result) == 1
        assert result[0] == mock_pvc

    @pytest.mark.asyncio
    async def test_list_pvcs_with_selectors(
        self, pvc_manager, k8s_client
    ):
        """셀렉터를 사용한 PVC 목록 조회"""
        mock_list = V1PersistentVolumeClaimList(items=[])
        k8s_client.core_v1.list_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_list
        )

        result = await pvc_manager.list_pvcs(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-pvc",
        )

        assert len(result) == 0
        k8s_client.core_v1.list_namespaced_persistent_volume_claim.assert_called_once_with(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-pvc",
        )

    @pytest.mark.asyncio
    async def test_list_pvcs_api_exception(
        self, pvc_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.list_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(PersistentVolumeClaimListException) as exc_info:
            await pvc_manager.list_pvcs(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """PVC 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """PVC 존재함"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )

        result = await pvc_manager.exists(name="test-pvc", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, pvc_manager, k8s_client):
        """PVC 존재하지 않음"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await pvc_manager.exists(name="test-pvc", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """PVC 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """레이블 병합 업데이트"""
        updated_pvc = V1PersistentVolumeClaim(
            metadata=V1ObjectMeta(
                name="test-pvc",
                namespace="test-ns",
                labels={"app": "test", "env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )
        k8s_client.core_v1.patch_namespaced_persistent_volume_claim = AsyncMock(
            return_value=updated_pvc
        )

        result = await pvc_manager.update_labels(
            name="test-pvc",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_pvc
        k8s_client.core_v1.patch_namespaced_persistent_volume_claim.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, pvc_manager, k8s_client):
        """존재하지 않는 PVC 레이블 업데이트"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(PersistentVolumeClaimUpdateException) as exc_info:
            await pvc_manager.update_labels(
                name="test-pvc",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)


class TestResizePVC:
    """PVC 크기 변경 테스트"""

    @pytest.mark.asyncio
    async def test_resize_pvc_success(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """PVC 크기 변경 성공"""
        updated_pvc = V1PersistentVolumeClaim(
            metadata=V1ObjectMeta(name="test-pvc", namespace="test-ns"),
            spec=V1PersistentVolumeClaimSpec(
                resources=V1ResourceRequirements(requests={"storage": "20Gi"})
            ),
        )

        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )
        k8s_client.core_v1.patch_namespaced_persistent_volume_claim = AsyncMock(
            return_value=updated_pvc
        )

        result = await pvc_manager.resize_pvc(
            name="test-pvc",
            namespace="test-ns",
            new_storage_size="20Gi",
        )

        assert result == updated_pvc
        k8s_client.core_v1.patch_namespaced_persistent_volume_claim.assert_called_once()

    @pytest.mark.asyncio
    async def test_resize_pvc_not_found(self, pvc_manager, k8s_client):
        """존재하지 않는 PVC 크기 변경"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(PersistentVolumeClaimUpdateException) as exc_info:
            await pvc_manager.resize_pvc(
                name="test-pvc",
                namespace="test-ns",
                new_storage_size="20Gi",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resize_pvc_api_exception(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )
        k8s_client.core_v1.patch_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(PersistentVolumeClaimUpdateException) as exc_info:
            await pvc_manager.resize_pvc(
                name="test-pvc",
                namespace="test-ns",
                new_storage_size="20Gi",
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestGetPVCStatus:
    """PVC 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_pvc_status_success(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """PVC 상태 조회 성공"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )

        result = await pvc_manager.get_pvc_status(
            name="test-pvc",
            namespace="test-ns",
        )

        assert result is not None
        assert result["phase"] == "Bound"
        assert result["access_modes"] == ["ReadWriteOnce"]
        assert result["capacity"] == {"storage": "10Gi"}

    @pytest.mark.asyncio
    async def test_get_pvc_status_not_found(
        self, pvc_manager, k8s_client
    ):
        """존재하지 않는 PVC 상태 조회"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await pvc_manager.get_pvc_status(
            name="test-pvc",
            namespace="test-ns",
        )

        assert result is None


class TestIsBound:
    """PVC 바인딩 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_is_bound_true(
        self, pvc_manager, k8s_client, mock_pvc
    ):
        """PVC가 바인딩됨"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=mock_pvc
        )

        result = await pvc_manager.is_bound(name="test-pvc", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_bound_false_pending(
        self, pvc_manager, k8s_client
    ):
        """PVC가 Pending 상태"""
        pending_pvc = V1PersistentVolumeClaim(
            metadata=V1ObjectMeta(name="test-pvc", namespace="test-ns"),
            spec=V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=V1ResourceRequirements(requests={"storage": "10Gi"}),
            ),
            status=V1PersistentVolumeClaimStatus(phase="Pending"),
        )

        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            return_value=pending_pvc
        )

        result = await pvc_manager.is_bound(name="test-pvc", namespace="test-ns")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_bound_not_found(
        self, pvc_manager, k8s_client
    ):
        """PVC 존재하지 않음"""
        k8s_client.core_v1.read_namespaced_persistent_volume_claim = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await pvc_manager.is_bound(name="test-pvc", namespace="test-ns")

        assert result is False
