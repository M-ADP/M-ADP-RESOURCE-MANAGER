import pytest
import src.api  # Initialize API package to avoid circular import issues
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1ResourceQuota, V1ResourceQuotaSpec, V1ResourceQuotaStatus,
    V1Deployment, V1DeploymentSpec, V1DeploymentStatus,
    V1PodTemplateSpec, V1PodSpec, V1Container, V1ResourceRequirements, V1LabelSelector,
    V1Volume, V1PersistentVolumeClaimVolumeSource,
    V1PersistentVolumeClaim, V1PersistentVolumeClaimSpec, V1PersistentVolumeClaimStatus,
    V1Pod, V1PodStatus, V1ObjectMeta,
)

from src.app.monitoring.project_resource_status_use_case import ProjectResourceStatusUseCase
from src.app.monitoring.app_resource_status_use_case import AppResourceStatusUseCase
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from src.infra.kubernetes.managers.deployment import DeploymentManager
from src.infra.kubernetes.managers.persistentvolumeclaim import PersistentVolumeClaimManager
from src.infra.kubernetes.managers.pod import PodManager
from src.infra.kubernetes.managers.node import NodeManager


@pytest.mark.asyncio
async def test_project_resource_status_use_case():
    mock_rq_manager = AsyncMock(spec=ResourceQuotaManager)

    rq = V1ResourceQuota(
        spec=V1ResourceQuotaSpec(
            hard={
                "limits.cpu": "4",
                "limits.memory": "8Gi",
                "requests.storage": "100Gi",
                "pods": "10",
            }
        ),
        status=V1ResourceQuotaStatus(
            used={
                "limits.cpu": "1",
                "limits.memory": "2Gi",
                "requests.storage": "20Gi",
                "pods": "2",
            }
        ),
    )
    mock_rq_manager.list_resource_quotas.return_value = [rq]

    use_case = ProjectResourceStatusUseCase(mock_rq_manager)
    result = await use_case("test-project")

    assert result.project_id == "test-project"
    assert result.cpu.limit == "4.0"
    assert result.cpu.used == "1.0"
    assert result.cpu.percentage == 25.0
    assert result.cpu.unit == "cores"
    assert result.memory.limit == "8.0"
    assert result.memory.used == "2.0"
    assert result.memory.percentage == 25.0
    assert result.memory.unit == "GiB"
    assert result.disk.limit == "100.0"
    assert result.disk.used == "20.0"
    assert result.disk.percentage == 20.0
    assert result.disk.unit == "GiB"
    assert result.instance.limit == 10
    assert result.instance.used == 2
    assert result.instance.percentage == 20.0


def _make_use_case(deployment, pods, node_stats, pvc=None):
    mock_dep_manager = AsyncMock(spec=DeploymentManager)
    mock_dep_manager.get_deployment.return_value = deployment

    mock_pod_manager = AsyncMock(spec=PodManager)
    mock_pod_manager.list_pods.return_value = pods

    mock_node_manager = AsyncMock(spec=NodeManager)
    mock_node_manager.get_node_volume_stats.return_value = node_stats

    mock_pvc_manager = AsyncMock(spec=PersistentVolumeClaimManager)
    if pvc:
        mock_pvc_manager.get_pvc.return_value = pvc

    return AppResourceStatusUseCase(
        mock_dep_manager, mock_pvc_manager, mock_pod_manager, mock_node_manager
    )


def _make_deployment(replicas=2, ready_replicas=1):
    container = V1Container(
        name="app",
        resources=V1ResourceRequirements(
            requests={"cpu": "500m", "memory": "1Gi"},
            limits={"cpu": "1", "memory": "2Gi"},
        ),
    )
    pvc_volume = V1Volume(
        name="app-volume",
        persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
            claim_name="test-app-pvc"
        ),
    )
    return V1Deployment(
        spec=V1DeploymentSpec(
            replicas=replicas,
            selector=V1LabelSelector(match_labels={"app": "test"}),
            template=V1PodTemplateSpec(
                spec=V1PodSpec(containers=[container], volumes=[pvc_volume])
            ),
        ),
        status=V1DeploymentStatus(ready_replicas=ready_replicas),
    )


def _make_pod(pod_name="test-app-xxx", node_name="node-1"):
    return V1Pod(
        metadata=V1ObjectMeta(name=pod_name, namespace="mdp-test-project"),
        spec=V1PodSpec(node_name=node_name, containers=[]),
        status=V1PodStatus(phase="Running"),
    )


@pytest.mark.asyncio
async def test_app_resource_status_kubelet_stats():
    """kubelet stats 정상 반환 시 실사용량이 반영되는지 검증"""
    deployment = _make_deployment()
    pod = _make_pod()

    # kubelet stats: 50Gi capacity, 20Gi used
    gib = 1024 ** 3
    node_stats = {
        "pods": [
            {
                "podRef": {"name": "test-app-xxx", "namespace": "mdp-test-project"},
                "volume": [
                    {
                        "name": "app-volume",
                        "capacityBytes": 50 * gib,
                        "usedBytes": 20 * gib,
                    }
                ],
            }
        ]
    }

    use_case = _make_use_case(deployment, [pod], node_stats)
    results = await use_case("test-project", ["test-app"])
    assert len(results) == 1
    result = results[0]

    assert result.cpu.limit == "2.0"
    assert result.cpu.used == "0.5"
    assert result.memory.limit == "4.0"
    assert result.memory.used == "1.0"

    # kubelet stats 기반: 50Gi limit, 20Gi used → 40%
    assert result.disk.limit == "50.0"
    assert result.disk.used == "20.0"
    assert result.disk.percentage == 40.0

    assert result.instance.limit == 2
    assert result.instance.used == 1
    assert result.instance.percentage == 50.0


@pytest.mark.asyncio
async def test_app_resource_status_fallback_to_pvc():
    """kubelet stats 실패 시 PVC capacity로 fallback되는지 검증"""
    deployment = _make_deployment()
    pod = _make_pod()

    pvc = V1PersistentVolumeClaim(
        spec=V1PersistentVolumeClaimSpec(
            resources=V1ResourceRequirements(requests={"storage": "50Gi"}),
        ),
        status=V1PersistentVolumeClaimStatus(
            phase="Bound",
            capacity={"storage": "50Gi"},
        ),
    )

    # 빈 stats → kubelet 조회 실패로 간주
    use_case = _make_use_case(deployment, [pod], node_stats={}, pvc=pvc)
    results = await use_case("test-project", ["test-app"])
    result = results[0]

    # fallback: PVC 50Gi limit, 50Gi used (Bound)
    assert result.disk.limit == "50.0"
    assert result.disk.used == "50.0"
    assert result.disk.percentage == 100.0


@pytest.mark.asyncio
async def test_app_resource_status_no_pvc():
    """PVC 없는 앱은 disk 0/0"""
    container = V1Container(
        name="app",
        resources=V1ResourceRequirements(
            requests={"cpu": "500m", "memory": "1Gi"},
            limits={"cpu": "1", "memory": "2Gi"},
        ),
    )
    deployment = V1Deployment(
        spec=V1DeploymentSpec(
            replicas=1,
            selector=V1LabelSelector(match_labels={"app": "test"}),
            template=V1PodTemplateSpec(
                spec=V1PodSpec(containers=[container], volumes=[])
            ),
        ),
        status=V1DeploymentStatus(ready_replicas=1),
    )

    use_case = _make_use_case(deployment, pods=[], node_stats={})
    results = await use_case("test-project", ["test-app"])
    result = results[0]

    assert result.disk.limit == "0.0"
    assert result.disk.used == "0.0"
    assert result.disk.percentage == 0.0
