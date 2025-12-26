"""NamespaceManager 유닛 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from kubernetes_asyncio.client import V1Namespace, V1ObjectMeta, V1NamespaceList, V1NamespaceStatus
from kubernetes_asyncio.client.rest import ApiException

from infra.kubernetes.client import KubernetesClient
from infra.kubernetes.managers.namespace import NamespaceManager
from infra.kubernetes.managers.namespace.exceptions import (
    NamespaceCreationException,
    NamespaceNotFoundException,
    NamespaceDeletionException,
    NamespaceUpdateException,
    NamespaceReadException,
    NamespaceListException,
)
from core.logger import Logger


@pytest.fixture
def mock_logger():
    """Mock Logger 픽스처"""
    logger = MagicMock(spec=Logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_k8s_client():
    """Mock KubernetesClient 픽스처"""
    client = MagicMock(spec=KubernetesClient)
    client.core_v1 = AsyncMock()
    return client


@pytest.fixture
def namespace_manager(mock_k8s_client, mock_logger):
    """NamespaceManager 픽스처"""
    return NamespaceManager(mock_k8s_client, mock_logger)


@pytest.fixture
def sample_namespace():
    """샘플 Namespace 객체"""
    return V1Namespace(
        api_version="v1",
        kind="Namespace",
        metadata=V1ObjectMeta(
            name="test-namespace",
            labels={"env": "test"},
            annotations={"description": "Test namespace"}
        ),
        status=V1NamespaceStatus(phase="Active")
    )


class TestNamespaceManagerInit:
    """NamespaceManager 초기화 테스트"""

    def test_init(self, namespace_manager, mock_k8s_client, mock_logger):
        """초기화 테스트"""
        assert namespace_manager.k8s_client == mock_k8s_client
        assert namespace_manager.logger == mock_logger

    def test_init_without_logger(self, mock_k8s_client):
        """로거 없이 초기화 테스트"""
        manager = NamespaceManager(mock_k8s_client)
        assert manager.k8s_client == mock_k8s_client
        assert manager.logger is not None  # 기본 Logger 생성됨


class TestCreateNamespace:
    """create_namespace 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_create_namespace_success(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """Namespace 생성 성공 테스트"""
        # get_namespace는 None 반환 (존재하지 않음)
        mock_k8s_client.core_v1.read_namespace.side_effect = ApiException(status=404)
        # create_namespace는 성공
        mock_k8s_client.core_v1.create_namespace.return_value = sample_namespace

        result = await namespace_manager.create_namespace(
            name="test-namespace",
            labels={"env": "test"}
        )

        assert result == sample_namespace
        mock_k8s_client.core_v1.create_namespace.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_namespace_already_exists(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """이미 존재하는 Namespace 생성 시 멱등성 테스트"""
        # get_namespace가 기존 Namespace 반환
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace

        result = await namespace_manager.create_namespace(name="test-namespace")

        # 기존 리소스를 그대로 반환
        assert result == sample_namespace
        # create는 호출되지 않아야 함
        mock_k8s_client.core_v1.create_namespace.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_namespace_conflict_409(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """409 Conflict 발생 시 처리 테스트"""
        # get_namespace는 처음엔 None, 두 번째는 존재
        mock_k8s_client.core_v1.read_namespace.side_effect = [
            ApiException(status=404),  # 첫 번째: 존재하지 않음
            sample_namespace           # 두 번째: 생성됨
        ]
        # create는 409 에러
        mock_k8s_client.core_v1.create_namespace.side_effect = ApiException(
            status=409, reason="AlreadyExists"
        )

        result = await namespace_manager.create_namespace(name="test-namespace")

        # 기존 리소스를 반환해야 함
        assert result == sample_namespace

    @pytest.mark.asyncio
    async def test_create_namespace_api_exception(
        self, namespace_manager, mock_k8s_client
    ):
        """API 예외 발생 시 커스텀 예외로 변환 테스트"""
        mock_k8s_client.core_v1.read_namespace.side_effect = ApiException(status=404)
        mock_k8s_client.core_v1.create_namespace.side_effect = ApiException(
            status=500, reason="InternalError"
        )

        with pytest.raises(NamespaceCreationException) as exc_info:
            await namespace_manager.create_namespace(name="test-namespace")

        assert "InternalError" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_namespace_unexpected_exception(
        self, namespace_manager, mock_k8s_client
    ):
        """예상치 못한 예외 발생 시 처리 테스트"""
        mock_k8s_client.core_v1.read_namespace.side_effect = ApiException(status=404)
        mock_k8s_client.core_v1.create_namespace.side_effect = Exception("Unexpected")

        with pytest.raises(NamespaceCreationException) as exc_info:
            await namespace_manager.create_namespace(name="test-namespace")

        assert "Unexpected" in str(exc_info.value)


class TestGetNamespace:
    """get_namespace 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_get_namespace_success(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """Namespace 조회 성공 테스트"""
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace

        result = await namespace_manager.get_namespace("test-namespace")

        assert result == sample_namespace
        mock_k8s_client.core_v1.read_namespace.assert_called_once_with(
            name="test-namespace"
        )

    @pytest.mark.asyncio
    async def test_get_namespace_not_found(
        self, namespace_manager, mock_k8s_client
    ):
        """Namespace가 존재하지 않을 때 None 반환 테스트"""
        mock_k8s_client.core_v1.read_namespace.side_effect = ApiException(status=404)

        result = await namespace_manager.get_namespace("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_namespace_api_exception(
        self, namespace_manager, mock_k8s_client
    ):
        """API 예외 발생 시 커스텀 예외로 변환 테스트"""
        mock_k8s_client.core_v1.read_namespace.side_effect = ApiException(
            status=500, reason="InternalError"
        )

        with pytest.raises(NamespaceReadException) as exc_info:
            await namespace_manager.get_namespace("test-namespace")

        assert exc_info.value.detail["api_status_code"] == 500

    @pytest.mark.asyncio
    async def test_get_namespace_unexpected_exception(
        self, namespace_manager, mock_k8s_client
    ):
        """예상치 못한 예외 발생 시 처리 테스트"""
        mock_k8s_client.core_v1.read_namespace.side_effect = Exception("Unexpected")

        with pytest.raises(NamespaceReadException):
            await namespace_manager.get_namespace("test-namespace")


class TestDeleteNamespace:
    """delete_namespace 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_delete_namespace_success(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """Namespace 삭제 성공 테스트"""
        # exists는 True 반환
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace
        mock_k8s_client.core_v1.delete_namespace.return_value = MagicMock()

        result = await namespace_manager.delete_namespace("test-namespace")

        assert result is True
        mock_k8s_client.core_v1.delete_namespace.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_namespace_not_exists(
        self, namespace_manager, mock_k8s_client
    ):
        """존재하지 않는 Namespace 삭제 시 성공 반환 테스트"""
        # exists는 False 반환
        mock_k8s_client.core_v1.read_namespace.side_effect = ApiException(status=404)

        result = await namespace_manager.delete_namespace("nonexistent")

        assert result is True
        # delete는 호출되지 않아야 함
        mock_k8s_client.core_v1.delete_namespace.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_namespace_already_deleted_404(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """삭제 중 404 발생 시 성공으로 처리 테스트"""
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace
        mock_k8s_client.core_v1.delete_namespace.side_effect = ApiException(status=404)

        result = await namespace_manager.delete_namespace("test-namespace")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_namespace_api_exception(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """API 예외 발생 시 커스텀 예외로 변환 테스트"""
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace
        mock_k8s_client.core_v1.delete_namespace.side_effect = ApiException(
            status=500, reason="InternalError"
        )

        with pytest.raises(NamespaceDeletionException) as exc_info:
            await namespace_manager.delete_namespace("test-namespace")

        assert "InternalError" in exc_info.value.detail["reason"]

    @pytest.mark.asyncio
    async def test_delete_namespace_with_grace_period(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """유예 시간 설정 테스트"""
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace
        mock_k8s_client.core_v1.delete_namespace.return_value = MagicMock()

        await namespace_manager.delete_namespace(
            "test-namespace", 
            grace_period_seconds=60
        )

        mock_k8s_client.core_v1.delete_namespace.assert_called_once_with(
            name="test-namespace",
            grace_period_seconds=60
        )


class TestListNamespaces:
    """list_namespaces 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_list_namespaces_success(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """Namespace 목록 조회 성공 테스트"""
        namespace_list = V1NamespaceList(items=[sample_namespace])
        mock_k8s_client.core_v1.list_namespace.return_value = namespace_list

        result = await namespace_manager.list_namespaces()

        assert len(result) == 1
        assert result[0] == sample_namespace

    @pytest.mark.asyncio
    async def test_list_namespaces_with_selectors(
        self, namespace_manager, mock_k8s_client
    ):
        """셀렉터를 사용한 목록 조회 테스트"""
        namespace_list = V1NamespaceList(items=[])
        mock_k8s_client.core_v1.list_namespace.return_value = namespace_list

        await namespace_manager.list_namespaces(
            label_selector="env=production",
            field_selector="metadata.name=default"
        )

        mock_k8s_client.core_v1.list_namespace.assert_called_once_with(
            label_selector="env=production",
            field_selector="metadata.name=default"
        )

    @pytest.mark.asyncio
    async def test_list_namespaces_api_exception(
        self, namespace_manager, mock_k8s_client
    ):
        """API 예외 발생 시 커스텀 예외로 변환 테스트"""
        mock_k8s_client.core_v1.list_namespace.side_effect = ApiException(
            status=500, reason="InternalError"
        )

        with pytest.raises(NamespaceListException) as exc_info:
            await namespace_manager.list_namespaces()

        assert exc_info.value.detail["api_status_code"] == 500


class TestExists:
    """exists 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """Namespace 존재 테스트"""
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace

        result = await namespace_manager.exists("test-namespace")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(
        self, namespace_manager, mock_k8s_client
    ):
        """Namespace 존재하지 않음 테스트"""
        mock_k8s_client.core_v1.read_namespace.side_effect = ApiException(status=404)

        result = await namespace_manager.exists("nonexistent")

        assert result is False


class TestUpdateLabels:
    """update_labels 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """레이블 병합 업데이트 테스트"""
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace
        
        updated_namespace = V1Namespace(
            metadata=V1ObjectMeta(
                name="test-namespace",
                labels={"env": "test", "version": "v1"}
            )
        )
        mock_k8s_client.core_v1.patch_namespace.return_value = updated_namespace

        result = await namespace_manager.update_labels(
            "test-namespace",
            {"version": "v1"},
            merge=True
        )

        # 기존 레이블과 병합되었는지 확인
        assert "env" in result.metadata.labels
        assert "version" in result.metadata.labels

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """레이블 완전 교체 테스트"""
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace
        
        updated_namespace = V1Namespace(
            metadata=V1ObjectMeta(
                name="test-namespace",
                labels={"new": "label"}
            )
        )
        mock_k8s_client.core_v1.patch_namespace.return_value = updated_namespace

        result = await namespace_manager.update_labels(
            "test-namespace",
            {"new": "label"},
            merge=False
        )

        mock_k8s_client.core_v1.patch_namespace.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_not_found(
        self, namespace_manager, mock_k8s_client
    ):
        """존재하지 않는 Namespace 업데이트 시 예외 테스트"""
        mock_k8s_client.core_v1.read_namespace.side_effect = ApiException(status=404)

        with pytest.raises(NamespaceNotFoundException):
            await namespace_manager.update_labels(
                "nonexistent",
                {"label": "value"}
            )

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """API 예외 발생 시 커스텀 예외로 변환 테스트"""
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace
        mock_k8s_client.core_v1.patch_namespace.side_effect = ApiException(
            status=500, reason="InternalError"
        )

        with pytest.raises(NamespaceUpdateException) as exc_info:
            await namespace_manager.update_labels(
                "test-namespace",
                {"label": "value"}
            )

        assert "InternalError" in exc_info.value.detail["reason"]


class TestGetNamespaceStatus:
    """get_namespace_status 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_get_namespace_status_active(
        self, namespace_manager, mock_k8s_client, sample_namespace
    ):
        """Active 상태 조회 테스트"""
        mock_k8s_client.core_v1.read_namespace.return_value = sample_namespace

        result = await namespace_manager.get_namespace_status("test-namespace")

        assert result == "Active"

    @pytest.mark.asyncio
    async def test_get_namespace_status_terminating(
        self, namespace_manager, mock_k8s_client
    ):
        """Terminating 상태 조회 테스트"""
        terminating_ns = V1Namespace(
            metadata=V1ObjectMeta(name="test-namespace"),
            status=V1NamespaceStatus(phase="Terminating")
        )
        mock_k8s_client.core_v1.read_namespace.return_value = terminating_ns

        result = await namespace_manager.get_namespace_status("test-namespace")

        assert result == "Terminating"

    @pytest.mark.asyncio
    async def test_get_namespace_status_not_found(
        self, namespace_manager, mock_k8s_client
    ):
        """존재하지 않는 Namespace 상태 조회 테스트"""
        mock_k8s_client.core_v1.read_namespace.side_effect = ApiException(status=404)

        result = await namespace_manager.get_namespace_status("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_namespace_status_no_status(
        self, namespace_manager, mock_k8s_client
    ):
        """상태 정보가 없는 Namespace 조회 테스트"""
        ns_without_status = V1Namespace(
            metadata=V1ObjectMeta(name="test-namespace"),
            status=None
        )
        mock_k8s_client.core_v1.read_namespace.return_value = ns_without_status

        result = await namespace_manager.get_namespace_status("test-namespace")

        assert result is None
