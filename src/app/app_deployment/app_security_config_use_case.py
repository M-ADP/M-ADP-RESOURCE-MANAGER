from fastapi import Depends
from src.core.project import ProjectId
from src.api.v1.app.schemas.security_response import AppSecurityConfigResponse, SecurityConfigInfo
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppSecurityConfigUseCase:
    """App 보안 설정 조회 UseCase"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        app_name: str,
        project_id: str,
    ) -> AppSecurityConfigResponse:
        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        configs = []
        for container in deployment.containers:
            sc = container.security_context
            limits = (container.resources or {}).get("limits", {})
            
            configs.append(
                SecurityConfigInfo(
                    container_name=container.name,
                    privileged=sc.privileged if sc else None,
                    run_as_non_root=sc.run_as_non_root if sc else None,
                    allow_privilege_escalation=sc.allow_privilege_escalation if sc else None,
                    read_only_root_filesystem=sc.read_only_root_filesystem if sc else None,
                    capabilities_add=sc.capabilities_add if sc else [],
                    cpu_limit=limits.get("cpu"),
                    memory_limit=limits.get("memory"),
                )
            )

        return AppSecurityConfigResponse(
            deployment_name=deployment.name,
            namespace=deployment.namespace,
            configs=configs,
        )
