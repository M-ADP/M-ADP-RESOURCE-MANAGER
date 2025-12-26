"""ServiceManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1Service,
    V1ObjectMeta,
    V1ServiceSpec,
    V1ServicePort,
    V1ServiceList,
    V1ServiceStatus,
    V1LoadBalancerStatus,
    V1LoadBalancerIngress,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from infra.kubernetes.managers.service import (
    ServiceManager,
    ServiceCreationException,
    ServiceReadException,
    ServiceUpdateException,
    ServiceDeletionException,
    ServiceListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClient Mock 픽스처"""
    client = MagicMock(spec=KubernetesClient)
    client.core_v1 = AsyncMock()
    return client


@pytest.fixture
def service_manager(k8s_client):
    """ServiceManager 픽스처"""
    return ServiceManager(k8s_client)


@pytest.fixture
def mock_service():
    """Mock V1Service 객체"""
    return V1Service(
        api_version="v1",
        kind="Service",
        metadata=V1ObjectMeta(
            name="test-service",
            namespace="test-ns",
            labels={"app": "test"},
            annotations={"key": "value"},
        ),
        spec=V1ServiceSpec(
            selector={"app": "test"},
            ports=[
                V1ServicePort(
                    name="http",
                    port=80,
                    target_port=8080,
                    protocol="TCP",
                )
            ],
            type="ClusterIP",
            cluster_ip="10.0.0.1",
        ),
    )


class TestServiceManagerInit:
    """ServiceManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = ServiceManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = ServiceManager(k8s_client)
        assert manager.logger is not None


class TestCreateService:
    """Service 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_service_success(
        self, service_manager, k8s_client, mock_service
    ):
        """Service 생성 성공"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_service = AsyncMock(
            return_value=mock_service
        )

        result = await service_manager.create_service(
            name="test-service",
            namespace="test-ns",
            selector={"app": "test"},
            ports=[{"name": "http", "port": 80, "target_port": 8080}],
            labels={"app": "test"},
            annotations={"key": "value"},
        )

        assert result == mock_service
        k8s_client.core_v1.create_namespaced_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_service_already_exists(
        self, service_manager, k8s_client, mock_service
    ):
        """이미 존재하는 Service 생성 (멱등성)"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )

        result = await service_manager.create_service(
            name="test-service",
            namespace="test-ns",
            selector={"app": "test"},
            ports=[{"port": 80}],
        )

        assert result == mock_service
        k8s_client.core_v1.create_namespaced_service.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_service_with_node_port(
        self, service_manager, k8s_client, mock_service
    ):
        """NodePort 타입 Service 생성"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_service = AsyncMock(
            return_value=mock_service
        )

        result = await service_manager.create_service(
            name="test-service",
            namespace="test-ns",
            selector={"app": "test"},
            ports=[{"port": 80, "node_port": 30080}],
            service_type="NodePort",
        )

        assert result == mock_service

    @pytest.mark.asyncio
    async def test_create_service_conflict_409(
        self, service_manager, k8s_client, mock_service
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_service,  # 재조회: 있음
            ]
        )
        k8s_client.core_v1.create_namespaced_service = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await service_manager.create_service(
            name="test-service",
            namespace="test-ns",
            selector={"app": "test"},
            ports=[{"port": 80}],
        )

        assert result == mock_service
        assert k8s_client.core_v1.read_namespaced_service.call_count == 2

    @pytest.mark.asyncio
    async def test_create_service_api_exception(
        self, service_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_service = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceCreationException) as exc_info:
            await service_manager.create_service(
                name="test-service",
                namespace="test-ns",
                selector={"app": "test"},
                ports=[{"port": 80}],
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_service_unexpected_exception(
        self, service_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.core_v1.create_namespaced_service = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ServiceCreationException) as exc_info:
            await service_manager.create_service(
                name="test-service",
                namespace="test-ns",
                selector={"app": "test"},
                ports=[{"port": 80}],
            )

        assert "Unexpected error" in str(exc_info.value)


class TestGetService:
    """Service 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_service_success(
        self, service_manager, k8s_client, mock_service
    ):
        """Service 조회 성공"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )

        result = await service_manager.get_service(
            name="test-service",
            namespace="test-ns",
        )

        assert result == mock_service

    @pytest.mark.asyncio
    async def test_get_service_not_found(
        self, service_manager, k8s_client
    ):
        """존재하지 않는 Service 조회 (404)"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await service_manager.get_service(
            name="test-service",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_service_api_exception(
        self, service_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceReadException) as exc_info:
            await service_manager.get_service(
                name="test-service",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_service_unexpected_exception(
        self, service_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ServiceReadException) as exc_info:
            await service_manager.get_service(
                name="test-service",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteService:
    """Service 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_service_success(
        self, service_manager, k8s_client, mock_service
    ):
        """Service 삭제 성공"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.delete_namespaced_service = AsyncMock()

        result = await service_manager.delete_service(
            name="test-service",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_service_not_exists(
        self, service_manager, k8s_client
    ):
        """존재하지 않는 Service 삭제 (멱등성)"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await service_manager.delete_service(
            name="test-service",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_service.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_service_already_deleted_404(
        self, service_manager, k8s_client, mock_service
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.delete_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await service_manager.delete_service(
            name="test-service",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_service_api_exception(
        self, service_manager, k8s_client, mock_service
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.delete_namespaced_service = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceDeletionException) as exc_info:
            await service_manager.delete_service(
                name="test-service",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_service_with_grace_period(
        self, service_manager, k8s_client, mock_service
    ):
        """Grace period 지정 삭제"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.delete_namespaced_service = AsyncMock()

        result = await service_manager.delete_service(
            name="test-service",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.core_v1.delete_namespaced_service.assert_called_once_with(
            name="test-service",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListServices:
    """Service 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_services_in_namespace(
        self, service_manager, k8s_client, mock_service
    ):
        """특정 네임스페이스 내 Service 목록 조회"""
        mock_list = V1ServiceList(items=[mock_service])
        k8s_client.core_v1.list_namespaced_service = AsyncMock(
            return_value=mock_list
        )

        result = await service_manager.list_services(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_service

    @pytest.mark.asyncio
    async def test_list_services_all_namespaces(
        self, service_manager, k8s_client, mock_service
    ):
        """전체 네임스페이스 Service 목록 조회"""
        mock_list = V1ServiceList(items=[mock_service])
        k8s_client.core_v1.list_service_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await service_manager.list_services()

        assert len(result) == 1
        assert result[0] == mock_service

    @pytest.mark.asyncio
    async def test_list_services_with_selectors(
        self, service_manager, k8s_client
    ):
        """셀렉터를 사용한 Service 목록 조회"""
        mock_list = V1ServiceList(items=[])
        k8s_client.core_v1.list_namespaced_service = AsyncMock(
            return_value=mock_list
        )

        result = await service_manager.list_services(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-service",
        )

        assert len(result) == 0
        k8s_client.core_v1.list_namespaced_service.assert_called_once_with(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-service",
        )

    @pytest.mark.asyncio
    async def test_list_services_api_exception(
        self, service_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.list_namespaced_service = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceListException) as exc_info:
            await service_manager.list_services(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """Service 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, service_manager, k8s_client, mock_service
    ):
        """Service 존재함"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )

        result = await service_manager.exists(name="test-service", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, service_manager, k8s_client):
        """Service 존재하지 않음"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await service_manager.exists(name="test-service", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """Service 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, service_manager, k8s_client, mock_service
    ):
        """레이블 병합 업데이트"""
        updated_service = V1Service(
            metadata=V1ObjectMeta(
                name="test-service",
                namespace="test-ns",
                labels={"app": "test", "env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.patch_namespaced_service = AsyncMock(
            return_value=updated_service
        )

        result = await service_manager.update_labels(
            name="test-service",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_service
        k8s_client.core_v1.patch_namespaced_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, service_manager, k8s_client, mock_service
    ):
        """레이블 교체 업데이트"""
        updated_service = V1Service(
            metadata=V1ObjectMeta(
                name="test-service",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.patch_namespaced_service = AsyncMock(
            return_value=updated_service
        )

        result = await service_manager.update_labels(
            name="test-service",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_service

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, service_manager, k8s_client):
        """존재하지 않는 Service 레이블 업데이트"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ServiceUpdateException) as exc_info:
            await service_manager.update_labels(
                name="test-service",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, service_manager, k8s_client, mock_service
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.patch_namespaced_service = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceUpdateException) as exc_info:
            await service_manager.update_labels(
                name="test-service",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestUpdateAnnotations:
    """Service 어노테이션 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_annotations_merge(
        self, service_manager, k8s_client, mock_service
    ):
        """어노테이션 병합 업데이트"""
        updated_service = V1Service(
            metadata=V1ObjectMeta(
                name="test-service",
                namespace="test-ns",
                annotations={"key": "value", "new-key": "new-value"},
            )
        )

        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.patch_namespaced_service = AsyncMock(
            return_value=updated_service
        )

        result = await service_manager.update_annotations(
            name="test-service",
            namespace="test-ns",
            annotations={"new-key": "new-value"},
            merge=True,
        )

        assert result == updated_service

    @pytest.mark.asyncio
    async def test_update_annotations_replace(
        self, service_manager, k8s_client, mock_service
    ):
        """어노테이션 교체 업데이트"""
        updated_service = V1Service(
            metadata=V1ObjectMeta(
                name="test-service",
                namespace="test-ns",
                annotations={"new-key": "new-value"},
            )
        )

        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.patch_namespaced_service = AsyncMock(
            return_value=updated_service
        )

        result = await service_manager.update_annotations(
            name="test-service",
            namespace="test-ns",
            annotations={"new-key": "new-value"},
            merge=False,
        )

        assert result == updated_service

    @pytest.mark.asyncio
    async def test_update_annotations_not_found(self, service_manager, k8s_client):
        """존재하지 않는 Service 어노테이션 업데이트"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ServiceUpdateException) as exc_info:
            await service_manager.update_annotations(
                name="test-service",
                namespace="test-ns",
                annotations={"key": "value"},
            )

        assert "does not exist" in str(exc_info.value)


class TestUpdateSelector:
    """Service selector 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_selector_success(
        self, service_manager, k8s_client, mock_service
    ):
        """Selector 업데이트 성공"""
        updated_service = V1Service(
            metadata=V1ObjectMeta(name="test-service", namespace="test-ns"),
            spec=V1ServiceSpec(selector={"app": "new-app"}),
        )

        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.patch_namespaced_service = AsyncMock(
            return_value=updated_service
        )

        result = await service_manager.update_selector(
            name="test-service",
            namespace="test-ns",
            selector={"app": "new-app"},
        )

        assert result == updated_service

    @pytest.mark.asyncio
    async def test_update_selector_not_found(self, service_manager, k8s_client):
        """존재하지 않는 Service selector 업데이트"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(ServiceUpdateException) as exc_info:
            await service_manager.update_selector(
                name="test-service",
                namespace="test-ns",
                selector={"app": "new-app"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_selector_api_exception(
        self, service_manager, k8s_client, mock_service
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )
        k8s_client.core_v1.patch_namespaced_service = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(ServiceUpdateException) as exc_info:
            await service_manager.update_selector(
                name="test-service",
                namespace="test-ns",
                selector={"app": "new-app"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestGetServiceEndpoints:
    """Service 엔드포인트 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_service_endpoints_cluster_ip(
        self, service_manager, k8s_client, mock_service
    ):
        """ClusterIP 타입 Service 엔드포인트 조회"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=mock_service
        )

        result = await service_manager.get_service_endpoints(
            name="test-service",
            namespace="test-ns",
        )

        assert result == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_get_service_endpoints_load_balancer(
        self, service_manager, k8s_client
    ):
        """LoadBalancer 타입 Service 엔드포인트 조회"""
        lb_service = V1Service(
            metadata=V1ObjectMeta(name="test-service", namespace="test-ns"),
            spec=V1ServiceSpec(
                type="LoadBalancer",
                cluster_ip="10.0.0.1",
            ),
            status=V1ServiceStatus(
                load_balancer=V1LoadBalancerStatus(
                    ingress=[V1LoadBalancerIngress(ip="203.0.113.1")]
                )
            ),
        )

        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            return_value=lb_service
        )

        result = await service_manager.get_service_endpoints(
            name="test-service",
            namespace="test-ns",
        )

        assert result == "203.0.113.1"

    @pytest.mark.asyncio
    async def test_get_service_endpoints_not_found(
        self, service_manager, k8s_client
    ):
        """존재하지 않는 Service 엔드포인트 조회"""
        k8s_client.core_v1.read_namespaced_service = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await service_manager.get_service_endpoints(
            name="test-service",
            namespace="test-ns",
        )

        assert result is None
