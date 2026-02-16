import pytest
import src.api # Initialize API package to avoid circular import issues
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import V1ResourceQuota, V1ResourceQuotaSpec, V1ResourceQuotaStatus, V1Deployment, V1DeploymentSpec, V1DeploymentStatus, V1PodTemplateSpec, V1PodSpec, V1Container, V1ResourceRequirements, V1LabelSelector

from src.app.monitoring.project_resource_status_use_case import ProjectResourceStatusUseCase
from src.app.monitoring.app_resource_status_use_case import AppResourceStatusUseCase
from src.infra.kubernetes.managers.resourcequota import ResourceQuotaManager
from src.infra.kubernetes.managers.deployment import DeploymentManager
from src.common.util.unit_converter import UnitConverter

@pytest.mark.asyncio
async def test_project_resource_status_use_case():
    # Mock ResourceQuotaManager
    mock_rq_manager = AsyncMock(spec=ResourceQuotaManager)
    
    # Mock Data
    rq = V1ResourceQuota(
        spec=V1ResourceQuotaSpec(
            hard={
                "limits.cpu": "4",
                "limits.memory": "8Gi",
                "requests.storage": "100Gi",
                "pods": "10"
            }
        ),
        status=V1ResourceQuotaStatus(
            used={
                "limits.cpu": "1",
                "limits.memory": "2Gi",
                "requests.storage": "20Gi",
                "pods": "2"
            }
        )
    )
    mock_rq_manager.list_resource_quotas.return_value = [rq]

    use_case = ProjectResourceStatusUseCase(mock_rq_manager)
    result = await use_case("test-project")

    assert result.project_id == "test-project"
    
    # CPU: 4 cores limit, 1 core used -> 25%
    assert result.cpu.limit == "4.0"
    assert result.cpu.used == "1.0"
    assert result.cpu.percentage == 25.0
    assert result.cpu.unit == "cores"

    # Memory: 8Gi limit, 2Gi used -> 25%
    assert result.memory.limit == "8.0"
    assert result.memory.used == "2.0"
    assert result.memory.percentage == 25.0
    assert result.memory.unit == "GiB"

    # Disk: 100Gi limit, 20Gi used -> 20%
    assert result.disk.limit == "100.0"
    assert result.disk.used == "20.0"
    assert result.disk.percentage == 20.0
    assert result.disk.unit == "GiB"

    # Instance: 10 limit, 2 used -> 20%
    assert result.instance.limit == 10
    assert result.instance.used == 2
    assert result.instance.percentage == 20.0

@pytest.mark.asyncio
async def test_app_resource_status_use_case():
    # Mock DeploymentManager
    mock_dep_manager = AsyncMock(spec=DeploymentManager)

    # Mock Data
    # 2 Replicas, 1 Container
    # Container: Request 0.5 CPU, 1Gi Mem; Limit 1 CPU, 2Gi Mem
    container = V1Container(
        name="app",
        resources=V1ResourceRequirements(
            requests={"cpu": "500m", "memory": "1Gi", "ephemeral-storage": "10Gi"},
            limits={"cpu": "1", "memory": "2Gi", "ephemeral-storage": "20Gi"}
        )
    )
    
    deployment = V1Deployment(
        spec=V1DeploymentSpec(
            replicas=2,
            selector=V1LabelSelector(match_labels={"app": "test"}),
            template=V1PodTemplateSpec(
                spec=V1PodSpec(
                    containers=[container]
                )
            )
        ),
        status=V1DeploymentStatus(
            ready_replicas=1 # 1 ready out of 2
        )
    )
    mock_dep_manager.get_deployment.return_value = deployment

    use_case = AppResourceStatusUseCase(mock_dep_manager)
    result = await use_case("test-project", "test-app")

    assert result.app_id == "test-app"
    assert result.project_id == "test-project"

    # CPU
    # Limit: 1 CPU * 2 replicas = 2.0
    # Used (Request * Ready): 0.5 CPU * 1 ready = 0.5
    # Wait, my implementation uses "Request * Used Replicas"?
    # Let's check implementation.
    # used_val = pod_requests * replicas_used
    # limit_val = pod_limits * replicas_limit
    
    # CPU: Limit 2.0, Used 0.5 -> 25%
    assert result.cpu.limit == "2.0"
    assert result.cpu.used == "0.5"
    assert result.cpu.percentage == 25.0
    
    # Memory
    # Limit: 2Gi * 2 = 4.0
    # Used: 1Gi * 1 = 1.0
    # 1/4 = 25%
    assert result.memory.limit == "4.0"
    assert result.memory.used == "1.0"
    assert result.memory.percentage == 25.0

    # Disk
    # Limit: 20Gi * 2 = 40.0
    # Used: 10Gi * 1 = 10.0
    # 10/40 = 25%
    assert result.disk.limit == "40.0"
    assert result.disk.used == "10.0"
    assert result.disk.percentage == 25.0

    # Instance
    # Limit: 2
    # Used: 1
    # 50%
    assert result.instance.limit == 2
    assert result.instance.used == 1
    assert result.instance.percentage == 50.0
