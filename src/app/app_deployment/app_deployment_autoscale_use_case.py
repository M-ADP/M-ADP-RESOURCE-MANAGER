"""App Deployment Auto Scale Use Case"""

from fastapi import Depends

from src.api.v1.app.schemas.request import AutoScaleRequest
from src.api.v1.app.schemas.response import AutoScaleResponse
from src.app.base_use_case import BaseUseCase
from src.common.const import DefaultLabel
from src.core.kubernetes.hpa import HorizontalPodAutoscaler
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.dependencies.kubernetes import get_deployment_repository, get_hpa_repository


class AppDeploymentAutoScaleUseCase(BaseUseCase):
    """App Deployment Auto Scale (HPA 생성/수정) Use Case"""

    def __init__(
        self,
        deployment_repository=Depends(get_deployment_repository),
        hpa_repository=Depends(get_hpa_repository),
    ):
        self.deployment_repository = deployment_repository
        self.hpa_repository = hpa_repository

    async def __call__(
        self,
        app_name: str,
        namespace: str,
        payload: AutoScaleRequest,
        user_id: str,
    ) -> AutoScaleResponse:
        """App에 HPA 설정"""

        # 1. Deployment 존재 확인
        deployment = await self.deployment_repository.find_by_name(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        # 2. HPA 이름 생성
        hpa_name = f"{app_name}-hpa"

        # 3. HPA 도메인 객체 생성
        hpa = HorizontalPodAutoscaler.for_deployment(
            name=hpa_name,
            namespace=namespace,
            deployment_name=app_name,
            min_replicas=payload.min_replicas,
            max_replicas=payload.max_replicas,
            target_cpu_utilization=payload.target_cpu_utilization,
            target_memory_utilization=payload.target_memory_utilization,
            labels={
                "app_deployment": app_name,
                "owner": user_id,
                **DefaultLabel.MANAGED_BY_LABEL,
            },
        )

        # 4. HPA 저장 (생성 또는 수정)
        saved_hpa = await self.hpa_repository.save(hpa)

        # 5. 응답 생성
        # CPU utilization 찾기
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
