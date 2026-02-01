import dataclasses
from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectResourceUpdateRequest
from src.app.base_use_case import BaseUseCase
from src.common.const import DefaultLabel
from src.common.util import UnitConverter
from src.dependencies.kubernetes import get_resource_quota_repository, get_limit_range_repository, get_vpa_repository
from src.core.kubernetes.resource_quota import ResourceQuotaRepository, ResourceQuota
from src.core.kubernetes.limit_range import LimitRangeRepository, LimitRange, LimitRangeItem
from src.app.project.exceptions import ResourceQuotaNotFoundException, DiskReductionNotAllowedException
from src.core.kubernetes.vpa import VpaRepository, VerticalPodAutoscaler

class ProjectResourceUpdateUseCase(BaseUseCase):

    def __init__(
            self,
            quota_repo: ResourceQuotaRepository = Depends(get_resource_quota_repository),
            # limit_repo: LimitRangeRepository = Depends(get_limit_range_repository),
            # vpa_repo: VpaRepository = Depends(get_vpa_repository),
    ):
        self.quota_repo = quota_repo
        # self.limit_repo = limit_repo
        # self.vpa_repo = vpa_repo

    async def __call__(
            self,
            project_name: str,
            payload: ProjectResourceUpdateRequest
    ) -> ResourceQuota:
        """Project의 리소스 할당량 (ResourceQuota, LimitRange, VPA)을 수정합니다."""

        # 1. ResourceQuota 업데이트
        updated_quota = await self._update_resource_quota(project_name, payload)

        # LimitRange와 VPA는 추후 추가하기로

        return updated_quota

    async def _update_resource_quota(self, project_name: str, payload: ProjectResourceUpdateRequest) -> ResourceQuota:
        """지정된 프로젝트(네임스페이스)의 ResourceQuota를 찾아 업데이트합니다."""
        quotas = await self.quota_repo.find_all(namespace=project_name, label_selector="managed-by=madp")
        if not quotas:
            raise ResourceQuotaNotFoundException()

        existing_quota = quotas[0]

        # 요청에 명시된 값만 업데이트하고, 나머지는 기존 값 유지
        new_limits_dict = existing_quota.hard_limits.copy()

        if payload.cpu:
            new_limits_dict["requests.cpu"] = payload.cpu
            new_limits_dict["limits.cpu"] = payload.cpu

        if payload.memory:
            new_limits_dict["requests.memory"] = payload.memory
            new_limits_dict["limits.memory"] = payload.memory

        if payload.disk:
            # DISK는 줄어들지 않는 보수적 정책 적용
            current_disk = existing_quota.hard_limits.get("requests.storage", "0")
            current_bytes = UnitConverter.parse_storage_to_bytes(current_disk)
            requested_bytes = UnitConverter.parse_storage_to_bytes(payload.disk)

            if requested_bytes < current_bytes:
                raise DiskReductionNotAllowedException(
                    current=current_disk,
                    requested=payload.disk,
                )

            new_limits_dict["requests.storage"] = payload.disk

        # dataclasses.replace를 사용하여 불변 객체의 복사본을 만듭니다.
        updated_quota_obj = dataclasses.replace(existing_quota, hard_limits=new_limits_dict)

        saved_quota = await self.quota_repo.save(updated_quota_obj)
        return saved_quota
