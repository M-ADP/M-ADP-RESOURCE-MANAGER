"""DeploymentManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1Deployment,
    V1ObjectMeta,
    V1DeploymentSpec,
    V1DeploymentList,
    V1LabelSelector,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
    V1DeploymentStatus,
    V1DeploymentCondition,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra.kubernetes.managers.deployment import (
    DeploymentManager,
    DeploymentCreationException,
    DeploymentReadException,
    DeploymentUpdateException,
    DeploymentDeletionException,
    DeploymentListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClientImpl Mock 픽스처"""
    client = MagicMock(spec=KubernetesClientImpl)
    client.apps_v1 = AsyncMock()
    return client


@pytest.fixture
def dep_manager(k8s_client):
    """DeploymentManager 픽스처"""
    return DeploymentManager(k8s_client)


@pytest.fixture
def mock_container():
    """Mock V1Container 객체"""
    return V1Container(
        name="test-container",
        image="nginx:latest",
        ports=[],
    )


@pytest.fixture
def mock_deployment(mock_container):
    """Mock V1Deployment 객체"""
    return V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=V1ObjectMeta(
            name="test-deployment",
            namespace="test-ns",
            labels={"app_deployment": "test"},
            annotations={"key": "value"},
        ),
        spec=V1DeploymentSpec(
            replicas=3,
            selector=V1LabelSelector(
                match_labels={"app_deployment": "test"},
            ),
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(
                    labels={"app_deployment": "test"},
                ),
                spec=V1PodSpec(
                    containers=[mock_container],
                ),
            ),
        ),
        status=V1DeploymentStatus(
            replicas=3,
            ready_replicas=3,
            available_replicas=3,
            updated_replicas=3,
            unavailable_replicas=0,
            conditions=[
                V1DeploymentCondition(
                    type="Available",
                    status="True",
                    reason="MinimumReplicasAvailable",
                    message="Deployment has minimum availability.",
                )
            ],
        ),
    )


class TestDeploymentManagerInit:
    """DeploymentManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = DeploymentManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = DeploymentManager(k8s_client)
        assert manager.logger is not None


class TestCreateDeployment:
    """Deployment 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_deployment_success(
        self, dep_manager, k8s_client, mock_deployment, mock_container
    ):
        """Deployment 생성 성공"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )

        result = await dep_manager.create_deployment(
            name="test-deployment",
            namespace="test-ns",
            containers=[mock_container],
            replicas=3,
            labels={"app_deployment": "test"},
            annotations={"key": "value"},
        )

        assert result == mock_deployment
        k8s_client.apps_v1.create_namespaced_deployment.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_deployment_already_exists(
        self, dep_manager, k8s_client, mock_deployment, mock_container
    ):
        """이미 존재하는 Deployment 생성 (멱등성)"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )

        result = await dep_manager.create_deployment(
            name="test-deployment",
            namespace="test-ns",
            containers=[mock_container],
        )

        assert result == mock_deployment
        k8s_client.apps_v1.create_namespaced_deployment.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_deployment_conflict_409(
        self, dep_manager, k8s_client, mock_deployment, mock_container
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_deployment,  # 재조회: 있음
            ]
        )
        k8s_client.apps_v1.create_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await dep_manager.create_deployment(
            name="test-deployment",
            namespace="test-ns",
            containers=[mock_container],
        )

        assert result == mock_deployment
        assert k8s_client.apps_v1.read_namespaced_deployment.call_count == 2

    @pytest.mark.asyncio
    async def test_create_deployment_api_exception(
        self, dep_manager, k8s_client, mock_container
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DeploymentCreationException) as exc_info:
            await dep_manager.create_deployment(
                name="test-deployment",
                namespace="test-ns",
                containers=[mock_container],
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_deployment_unexpected_exception(
        self, dep_manager, k8s_client, mock_container
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.apps_v1.create_namespaced_deployment = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(DeploymentCreationException) as exc_info:
            await dep_manager.create_deployment(
                name="test-deployment",
                namespace="test-ns",
                containers=[mock_container],
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetDeployment:
    """Deployment 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_deployment_success(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """Deployment 조회 성공"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )

        result = await dep_manager.get_deployment(
            name="test-deployment",
            namespace="test-ns",
        )

        assert result == mock_deployment

    @pytest.mark.asyncio
    async def test_get_deployment_not_found(
        self, dep_manager, k8s_client
    ):
        """존재하지 않는 Deployment 조회 (404)"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await dep_manager.get_deployment(
            name="test-deployment",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_deployment_api_exception(
        self, dep_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DeploymentReadException) as exc_info:
            await dep_manager.get_deployment(
                name="test-deployment",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_deployment_unexpected_exception(
        self, dep_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(DeploymentReadException) as exc_info:
            await dep_manager.get_deployment(
                name="test-deployment",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteDeployment:
    """Deployment 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_deployment_success(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """Deployment 삭제 성공"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )
        k8s_client.apps_v1.delete_namespaced_deployment = AsyncMock()

        result = await dep_manager.delete_deployment(
            name="test-deployment",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.apps_v1.delete_namespaced_deployment.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_deployment_not_exists(
        self, dep_manager, k8s_client
    ):
        """존재하지 않는 Deployment 삭제"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(DeploymentDeletionException) as exc_info:
            await dep_manager.delete_deployment(
                name="test-deployment",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_deployment_already_deleted_404(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )
        k8s_client.apps_v1.delete_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await dep_manager.delete_deployment(
            name="test-deployment",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_deployment_api_exception(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )
        k8s_client.apps_v1.delete_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DeploymentDeletionException) as exc_info:
            await dep_manager.delete_deployment(
                name="test-deployment",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_deployment_with_grace_period(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """Grace period 지정 삭제"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )
        k8s_client.apps_v1.delete_namespaced_deployment = AsyncMock()

        result = await dep_manager.delete_deployment(
            name="test-deployment",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.apps_v1.delete_namespaced_deployment.assert_called_once_with(
            name="test-deployment",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListDeployments:
    """Deployment 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_deployments_in_namespace(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """특정 네임스페이스 내 Deployment 목록 조회"""
        mock_list = V1DeploymentList(items=[mock_deployment])
        k8s_client.apps_v1.list_namespaced_deployment = AsyncMock(
            return_value=mock_list
        )

        result = await dep_manager.list_deployments(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_deployment

    @pytest.mark.asyncio
    async def test_list_deployments_all_namespaces(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """전체 네임스페이스 Deployment 목록 조회"""
        mock_list = V1DeploymentList(items=[mock_deployment])
        k8s_client.apps_v1.list_deployment_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await dep_manager.list_deployments()

        assert len(result) == 1
        assert result[0] == mock_deployment

    @pytest.mark.asyncio
    async def test_list_deployments_with_selectors(
        self, dep_manager, k8s_client
    ):
        """셀렉터를 사용한 Deployment 목록 조회"""
        mock_list = V1DeploymentList(items=[])
        k8s_client.apps_v1.list_namespaced_deployment = AsyncMock(
            return_value=mock_list
        )

        result = await dep_manager.list_deployments(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-deployment",
        )

        assert len(result) == 0
        k8s_client.apps_v1.list_namespaced_deployment.assert_called_once_with(
            namespace="test-ns",
            label_selector="app_deployment=test",
            field_selector="metadata.name=test-deployment",
        )

    @pytest.mark.asyncio
    async def test_list_deployments_api_exception(
        self, dep_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.list_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DeploymentListException) as exc_info:
            await dep_manager.list_deployments(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """Deployment 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """Deployment 존재함"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )

        result = await dep_manager.exists(name="test-deployment", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, dep_manager, k8s_client):
        """Deployment 존재하지 않음"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await dep_manager.exists(name="test-deployment", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """Deployment 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """레이블 병합 업데이트"""
        updated_dep = V1Deployment(
            metadata=V1ObjectMeta(
                name="test-deployment",
                namespace="test-ns",
                labels={"app_deployment": "test", "env": "prod"},
            )
        )

        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )
        k8s_client.apps_v1.patch_namespaced_deployment = AsyncMock(
            return_value=updated_dep
        )

        result = await dep_manager.update_labels(
            name="test-deployment",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_dep
        k8s_client.apps_v1.patch_namespaced_deployment.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """레이블 교체 업데이트"""
        updated_dep = V1Deployment(
            metadata=V1ObjectMeta(
                name="test-deployment",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )
        k8s_client.apps_v1.patch_namespaced_deployment = AsyncMock(
            return_value=updated_dep
        )

        result = await dep_manager.update_labels(
            name="test-deployment",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_dep

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, dep_manager, k8s_client):
        """존재하지 않는 Deployment 레이블 업데이트"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(DeploymentUpdateException) as exc_info:
            await dep_manager.update_labels(
                name="test-deployment",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )
        k8s_client.apps_v1.patch_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DeploymentUpdateException) as exc_info:
            await dep_manager.update_labels(
                name="test-deployment",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestUpdateReplicas:
    """Deployment 레플리카 수 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_replicas_success(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """레플리카 수 업데이트 성공"""
        updated_dep = V1Deployment(
            metadata=V1ObjectMeta(
                name="test-deployment",
                namespace="test-ns",
            ),
            spec=V1DeploymentSpec(
                replicas=5,
                selector=V1LabelSelector(match_labels={"app_deployment": "test"}),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app_deployment": "test"}),
                    spec=V1PodSpec(containers=[]),
                ),
            ),
        )

        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )
        k8s_client.apps_v1.patch_namespaced_deployment = AsyncMock(
            return_value=updated_dep
        )

        result = await dep_manager.update_replicas(
            name="test-deployment",
            namespace="test-ns",
            replicas=5,
        )

        assert result == updated_dep
        k8s_client.apps_v1.patch_namespaced_deployment.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_replicas_not_found(self, dep_manager, k8s_client):
        """존재하지 않는 Deployment 레플리카 수 업데이트"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(DeploymentUpdateException) as exc_info:
            await dep_manager.update_replicas(
                name="test-deployment",
                namespace="test-ns",
                replicas=5,
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_replicas_api_exception(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """API 예외 발생 시"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )
        k8s_client.apps_v1.patch_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(DeploymentUpdateException) as exc_info:
            await dep_manager.update_replicas(
                name="test-deployment",
                namespace="test-ns",
                replicas=5,
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestGetDeploymentStatus:
    """Deployment 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_deployment_status_success(
        self, dep_manager, k8s_client, mock_deployment
    ):
        """Deployment 상태 조회 성공"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=mock_deployment
        )

        result = await dep_manager.get_deployment_status(
            name="test-deployment",
            namespace="test-ns",
        )

        assert result is not None
        assert result["replicas"] == 3
        assert result["ready_replicas"] == 3
        assert result["available_replicas"] == 3
        assert result["updated_replicas"] == 3
        assert result["unavailable_replicas"] == 0
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "Available"

    @pytest.mark.asyncio
    async def test_get_deployment_status_not_found(
        self, dep_manager, k8s_client
    ):
        """존재하지 않는 Deployment 상태 조회"""
        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await dep_manager.get_deployment_status(
            name="test-deployment",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_deployment_status_no_status(
        self, dep_manager, k8s_client
    ):
        """Status가 없는 Deployment"""
        deployment_no_status = V1Deployment(
            metadata=V1ObjectMeta(
                name="test-deployment",
                namespace="test-ns",
            ),
            spec=V1DeploymentSpec(
                replicas=1,
                selector=V1LabelSelector(match_labels={"app_deployment": "test"}),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app_deployment": "test"}),
                    spec=V1PodSpec(containers=[]),
                ),
            ),
        )

        k8s_client.apps_v1.read_namespaced_deployment = AsyncMock(
            return_value=deployment_no_status
        )

        result = await dep_manager.get_deployment_status(
            name="test-deployment",
            namespace="test-ns",
        )

        assert result is None
