"""App Deployment Auto Scale Use Case"""

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.app.schemas.request import AutoScaleRequest
from src.api.v1.app.schemas.response import AutoScaleResponse
from src.app.base_use_case import BaseUseCase
from src.common.util import NameConverter
from src.common.const import DefaultLabel
from src.core.app_deployment import AppDeploymentRepository
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.dependencies.kubernetes import get_app_deployment_repository


class AppDeploymentAutoScaleUseCase(BaseUseCase):
    """App Deployment Auto Scale (HPA 생성/수정) Use Case"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        app_name: str,
        project_id: str,
        payload: AutoScaleRequest,
    ) -> AutoScaleResponse:
        """App에 HPA 설정"""

        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        # 1. Deployment 조회
        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        # 2. Deployment에서 HPA 도메인 객체 생성 (naming은 deployment이 결정)
        hpa = deployment.create_hpa(
            min_replicas=payload.min_replicas,
            max_replicas=payload.max_replicas,
            target_cpu_utilization=payload.target_cpu_utilization,
            target_memory_utilization=payload.target_memory_utilization,
            labels={
                "app_deployment": deployment.name,
                **DefaultLabel.MANAGED_BY_LABEL,
            },
        )

        # 3. 오토스케일 활성화
        saved_hpa = await self.app_deployment_repo.enable_autoscale(hpa)

        target_cpu = None
        target_memory = None
        for metric in saved_hpa.metrics:
            if metric.resource_name == "cpu":
                target_cpu = metric.target_value
            elif metric.resource_name == "memory":
                target_memory = metric.target_value

        return AutoScaleResponse(
            name=saved_hpa.name,
            namespace=saved_hpa.namespace,
            deployment_name=saved_hpa.scale_target_ref.name,
            min_replicas=saved_hpa.min_replicas,
            max_replicas=saved_hpa.max_replicas,
            target_cpu_utilization=target_cpu,
            target_memory_utilization=target_memory,
            current_replicas=saved_hpa.status.current_replicas if saved_hpa.status else None,
            desired_replicas=saved_hpa.status.desired_replicas if saved_hpa.status else None,
        )
