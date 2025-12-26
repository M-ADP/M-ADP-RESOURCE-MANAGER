"""PodManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from kubernetes_asyncio.client import (
    V1Pod,
    V1ObjectMeta,
    V1PodSpec,
    V1PodList,
    V1Container,
    V1PodStatus,
    V1PodCondition,
    V1ContainerStatus,
    V1ContainerState,
    V1ContainerStateRunning,
    V1ContainerStateWaiting,
    V1ContainerStateTerminated,
    V1OwnerReference,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from infra.kubernetes.managers.pod import (
    PodManager,
    PodReadException,
    PodListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClient Mock 픽스처"""
    client = MagicMock(spec=KubernetesClient)
    client.core_v1 = AsyncMock()
    return client


@pytest.fixture
def pod_manager(k8s_client):
    """PodManager 픽스처"""
    return PodManager(k8s_client)


@pytest.fixture
def mock_pod():
    """Mock V1Pod 객체"""
    return V1Pod(
        api_version="v1",
        kind="Pod",
        metadata=V1ObjectMeta(
            name="test-pod",
            namespace="test-ns",
            labels={"app": "test"},
            owner_references=[
                V1OwnerReference(
                    api_version="apps/v1",
                    kind="Deployment",
                    name="test-deployment",
                    uid="test-uid",
                )
            ],
        ),
        spec=V1PodSpec(
            containers=[
                V1Container(
                    name="test-container",
                    image="nginx:latest",
                )
            ],
        ),
        status=V1PodStatus(
            phase="Running",
            pod_ip="10.0.0.1",
            host_ip="192.168.1.1",
            start_time=datetime.now(),
            conditions=[
                V1PodCondition(
                    type="Ready",
                    status="True",
                    reason="ContainersReady",
                    message="All containers are ready",
                )
            ],
            container_statuses=[
                V1ContainerStatus(
                    name="test-container",
                    ready=True,
                    restart_count=0,
                    image="nginx:latest",
                    image_id="docker-pullable://nginx@sha256:abc123",
                    state=V1ContainerState(
                        running=V1ContainerStateRunning(
                            started_at=datetime.now(),
                        )
                    ),
                )
            ],
        ),
    )


class TestPodManagerInit:
    """PodManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = PodManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = PodManager(k8s_client)
        assert manager.logger is not None


class TestGetPod:
    """Pod 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_pod_success(
        self, pod_manager, k8s_client, mock_pod
    ):
        """Pod 조회 성공"""
        k8s_client.core_v1.read_namespaced_pod = AsyncMock(
            return_value=mock_pod
        )

        result = await pod_manager.get_pod(
            name="test-pod",
            namespace="test-ns",
        )

        assert result == mock_pod

    @pytest.mark.asyncio
    async def test_get_pod_not_found(
        self, pod_manager, k8s_client
    ):
        """존재하지 않는 Pod 조회 (404)"""
        k8s_client.core_v1.read_namespaced_pod = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await pod_manager.get_pod(
            name="test-pod",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_pod_api_exception(
        self, pod_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_pod = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(PodReadException) as exc_info:
            await pod_manager.get_pod(
                name="test-pod",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_pod_unexpected_exception(
        self, pod_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_pod = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(PodReadException) as exc_info:
            await pod_manager.get_pod(
                name="test-pod",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestListPods:
    """Pod 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_pods_in_namespace(
        self, pod_manager, k8s_client, mock_pod
    ):
        """특정 네임스페이스 내 Pod 목록 조회"""
        mock_list = V1PodList(items=[mock_pod])
        k8s_client.core_v1.list_namespaced_pod = AsyncMock(
            return_value=mock_list
        )

        result = await pod_manager.list_pods(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_pod

    @pytest.mark.asyncio
    async def test_list_pods_all_namespaces(
        self, pod_manager, k8s_client, mock_pod
    ):
        """전체 네임스페이스 Pod 목록 조회"""
        mock_list = V1PodList(items=[mock_pod])
        k8s_client.core_v1.list_pod_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await pod_manager.list_pods()

        assert len(result) == 1
        assert result[0] == mock_pod

    @pytest.mark.asyncio
    async def test_list_pods_with_selectors(
        self, pod_manager, k8s_client
    ):
        """셀렉터를 사용한 Pod 목록 조회"""
        mock_list = V1PodList(items=[])
        k8s_client.core_v1.list_namespaced_pod = AsyncMock(
            return_value=mock_list
        )

        result = await pod_manager.list_pods(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-pod",
        )

        assert len(result) == 0
        k8s_client.core_v1.list_namespaced_pod.assert_called_once_with(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-pod",
        )

    @pytest.mark.asyncio
    async def test_list_pods_api_exception(
        self, pod_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.list_namespaced_pod = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(PodListException) as exc_info:
            await pod_manager.list_pods(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """Pod 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, pod_manager, k8s_client, mock_pod
    ):
        """Pod 존재함"""
        k8s_client.core_v1.read_namespaced_pod = AsyncMock(
            return_value=mock_pod
        )

        result = await pod_manager.exists(name="test-pod", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, pod_manager, k8s_client):
        """Pod 존재하지 않음"""
        k8s_client.core_v1.read_namespaced_pod = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await pod_manager.exists(name="test-pod", namespace="test-ns")

        assert result is False


class TestGetPodStatus:
    """Pod 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_pod_status_success(
        self, pod_manager, k8s_client, mock_pod
    ):
        """Pod 상태 조회 성공"""
        k8s_client.core_v1.read_namespaced_pod = AsyncMock(
            return_value=mock_pod
        )

        result = await pod_manager.get_pod_status(
            name="test-pod",
            namespace="test-ns",
        )

        assert result is not None
        assert result["phase"] == "Running"
        assert result["pod_ip"] == "10.0.0.1"
        assert result["host_ip"] == "192.168.1.1"
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "Ready"
        assert len(result["container_statuses"]) == 1
        assert result["container_statuses"][0]["name"] == "test-container"
        assert result["container_statuses"][0]["ready"] is True
        assert result["container_statuses"][0]["state"]["state"] == "Running"

    @pytest.mark.asyncio
    async def test_get_pod_status_not_found(
        self, pod_manager, k8s_client
    ):
        """존재하지 않는 Pod 상태 조회"""
        k8s_client.core_v1.read_namespaced_pod = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await pod_manager.get_pod_status(
            name="test-pod",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_pod_status_no_status(
        self, pod_manager, k8s_client
    ):
        """Status가 없는 Pod"""
        pod_no_status = V1Pod(
            metadata=V1ObjectMeta(
                name="test-pod",
                namespace="test-ns",
            ),
            spec=V1PodSpec(
                containers=[],
            ),
        )

        k8s_client.core_v1.read_namespaced_pod = AsyncMock(
            return_value=pod_no_status
        )

        result = await pod_manager.get_pod_status(
            name="test-pod",
            namespace="test-ns",
        )

        assert result is None


class TestGetContainerState:
    """컨테이너 상태 추출 테스트"""

    def test_container_state_running(self, pod_manager):
        """Running 상태"""
        container_status = V1ContainerStatus(
            name="test",
            ready=True,
            restart_count=0,
            image="nginx",
            image_id="docker-pullable://nginx@sha256:abc123",
            state=V1ContainerState(
                running=V1ContainerStateRunning(started_at=datetime.now())
            ),
        )

        state = pod_manager._get_container_state(container_status)

        assert state["state"] == "Running"
        assert "started_at" in state

    def test_container_state_waiting(self, pod_manager):
        """Waiting 상태"""
        container_status = V1ContainerStatus(
            name="test",
            ready=False,
            restart_count=0,
            image="nginx",
            image_id="docker-pullable://nginx@sha256:abc123",
            state=V1ContainerState(
                waiting=V1ContainerStateWaiting(
                    reason="ContainerCreating",
                    message="Waiting for container to start",
                )
            ),
        )

        state = pod_manager._get_container_state(container_status)

        assert state["state"] == "Waiting"
        assert state["reason"] == "ContainerCreating"
        assert state["message"] == "Waiting for container to start"

    def test_container_state_terminated(self, pod_manager):
        """Terminated 상태"""
        container_status = V1ContainerStatus(
            name="test",
            ready=False,
            restart_count=1,
            image="nginx",
            image_id="docker-pullable://nginx@sha256:abc123",
            state=V1ContainerState(
                terminated=V1ContainerStateTerminated(
                    exit_code=1,
                    reason="Error",
                    message="Container failed",
                    started_at=datetime.now(),
                    finished_at=datetime.now(),
                )
            ),
        )

        state = pod_manager._get_container_state(container_status)

        assert state["state"] == "Terminated"
        assert state["exit_code"] == 1
        assert state["reason"] == "Error"
        assert state["message"] == "Container failed"

    def test_container_state_no_state(self, pod_manager):
        """상태 정보 없음"""
        container_status = V1ContainerStatus(
            name="test",
            ready=False,
            restart_count=0,
            image="nginx",
            image_id="docker-pullable://nginx@sha256:abc123",
            state=None,
        )

        state = pod_manager._get_container_state(container_status)

        assert state["state"] == "Unknown"


class TestGetPodLogs:
    """Pod 로그 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_pod_logs_success(
        self, pod_manager, k8s_client
    ):
        """Pod 로그 조회 성공"""
        k8s_client.core_v1.read_namespaced_pod_log = AsyncMock(
            return_value="Log line 1\nLog line 2\n"
        )

        result = await pod_manager.get_pod_logs(
            name="test-pod",
            namespace="test-ns",
        )

        assert result == "Log line 1\nLog line 2\n"

    @pytest.mark.asyncio
    async def test_get_pod_logs_with_options(
        self, pod_manager, k8s_client
    ):
        """옵션을 사용한 Pod 로그 조회"""
        k8s_client.core_v1.read_namespaced_pod_log = AsyncMock(
            return_value="Recent log\n"
        )

        result = await pod_manager.get_pod_logs(
            name="test-pod",
            namespace="test-ns",
            container="test-container",
            tail_lines=100,
            since_seconds=3600,
            timestamps=True,
        )

        assert result == "Recent log\n"
        k8s_client.core_v1.read_namespaced_pod_log.assert_called_once_with(
            name="test-pod",
            namespace="test-ns",
            container="test-container",
            tail_lines=100,
            since_seconds=3600,
            timestamps=True,
        )

    @pytest.mark.asyncio
    async def test_get_pod_logs_not_found(
        self, pod_manager, k8s_client
    ):
        """존재하지 않는 Pod 로그 조회"""
        k8s_client.core_v1.read_namespaced_pod_log = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await pod_manager.get_pod_logs(
            name="test-pod",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_pod_logs_api_exception(
        self, pod_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.core_v1.read_namespaced_pod_log = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(PodReadException) as exc_info:
            await pod_manager.get_pod_logs(
                name="test-pod",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestListPodsByOwner:
    """소유자별 Pod 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_pods_by_owner_success(
        self, pod_manager, k8s_client, mock_pod
    ):
        """소유자별 Pod 목록 조회 성공"""
        mock_list = V1PodList(items=[mock_pod])
        k8s_client.core_v1.list_namespaced_pod = AsyncMock(
            return_value=mock_list
        )

        result = await pod_manager.list_pods_by_owner(
            owner_name="test-deployment",
            owner_kind="Deployment",
            namespace="test-ns",
        )

        assert len(result) == 1
        assert result[0] == mock_pod

    @pytest.mark.asyncio
    async def test_list_pods_by_owner_no_match(
        self, pod_manager, k8s_client, mock_pod
    ):
        """일치하는 소유자가 없는 경우"""
        mock_list = V1PodList(items=[mock_pod])
        k8s_client.core_v1.list_namespaced_pod = AsyncMock(
            return_value=mock_list
        )

        result = await pod_manager.list_pods_by_owner(
            owner_name="other-deployment",
            owner_kind="Deployment",
            namespace="test-ns",
        )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_pods_by_owner_no_owner_refs(
        self, pod_manager, k8s_client
    ):
        """OwnerReference가 없는 Pod"""
        pod_no_owner = V1Pod(
            metadata=V1ObjectMeta(
                name="test-pod",
                namespace="test-ns",
            ),
            spec=V1PodSpec(containers=[]),
        )

        mock_list = V1PodList(items=[pod_no_owner])
        k8s_client.core_v1.list_namespaced_pod = AsyncMock(
            return_value=mock_list
        )

        result = await pod_manager.list_pods_by_owner(
            owner_name="test-deployment",
            owner_kind="Deployment",
            namespace="test-ns",
        )

        assert len(result) == 0
