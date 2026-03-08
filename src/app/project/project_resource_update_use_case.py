from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectResourceUpdateRequest
from src.app.base_use_case import BaseUseCase
from src.common.util import UnitConverter
from src.core.project import ProjectRepository
from src.core.kubernetes.resource_quota import ResourceQuota
from src.app.project.exceptions import ResourceQuotaNotFoundException, DiskReductionNotAllowedException
from src.dependencies.kubernetes import get_project_repository


class ProjectResourceUpdateUseCase(BaseUseCase):

    def __init__(
            self,
            project_repo: ProjectRepository = Depends(get_project_repository),
    ):
        self.project_repo = project_repo

    async def __call__(
            self,
            project_id: str,
            payload: ProjectResourceUpdateRequest
    ) -> ResourceQuota:
        """Project의 리소스 할당량 (ResourceQuota)을 수정합니다."""
        return await self._update_resource_quota(project_id, payload)

    async def _update_resource_quota(self, project_id: str, payload: ProjectResourceUpdateRequest) -> ResourceQuota:
        quotas = await self.project_repo.find_all_resource_quotas(
            namespace=f"project-{project_id}",
            label_selector="managed-by=madp",
        )
        if not quotas:
            raise ResourceQuotaNotFoundException()

        quota = quotas[0]

        if payload.cpu:
            quota = quota.with_cpu(payload.cpu)

        if payload.memory:
            quota = quota.with_memory(payload.memory)

        if payload.disk:
            current_bytes = UnitConverter.parse_storage_to_bytes(
                quota.hard_limits.get("requests.storage", "0")
            )
            requested_bytes = UnitConverter.parse_storage_to_bytes(payload.disk)

            if requested_bytes < current_bytes:
                raise DiskReductionNotAllowedException(
                    current=quota.hard_limits.get("requests.storage", "0"),
                    requested=payload.disk,
                )

            quota = quota.with_disk(payload.disk)

        return await self.project_repo.save_resource_quota(quota)
