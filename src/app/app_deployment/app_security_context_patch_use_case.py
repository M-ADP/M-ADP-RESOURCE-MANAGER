from typing import List, Optional

from fastapi import Depends

from src.core.project import ProjectId
from src.api.v1.app.schemas.security_response import (
    AppSecurityContextPatchResponse,
    SecurityConfigInfo,
)
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository


class AppSecurityContextPatchUseCase:
    """App 보안 컨텍스트 패치 UseCase"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        app_name: str,
        project_id: str,
        run_as_non_root: Optional[bool] = None,
        allow_privilege_escalation: Optional[bool] = None,
        read_only_root_filesystem: Optional[bool] = None,
        privileged: Optional[bool] = None,
        capabilities_drop: Optional[List[str]] = None,
    ) -> AppSecurityContextPatchResponse:
        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        updated = await self.app_deployment_repo.patch_security_context(
            deployment=deployment,
            run_as_non_root=run_as_non_root,
            allow_privilege_escalation=allow_privilege_escalation,
            read_only_root_filesystem=read_only_root_filesystem,
            privileged=privileged,
            capabilities_drop=capabilities_drop,
        )

        configs = []
        for container in updated.containers:
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

        return AppSecurityContextPatchResponse(
            deployment_name=updated.name,
            namespace=updated.namespace,
            patched_containers=[c.name for c in updated.containers],
            configs=configs,
        )
