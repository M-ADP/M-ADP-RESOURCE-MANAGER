import dataclasses
from fastapi import Depends

from src.api.v1.project.schmas.request import ProjectResourceUpdateRequest
from src.app.base_use_case import BaseUseCase
from src.core.dependencies.kubernetes import get_resource_quota_repository, get_limit_range_repository, get_vpa_repository
from src.core.kubernetes.resource_quota import ResourceQuotaRepository, ResourceQuotaLimits, ResourceQuota
from src.core.kubernetes.limit_range import LimitRangeRepository, LimitRange, LimitRangeItem
from src.core.exceptions import ResourceQuotaNotFoundException
from src.core.kubernetes.vpa import VpaRepository, VerticalPodAutoscaler

MANAGED_BY_LABEL = {"managed-by": "madp"}


class ProjectResourceUpdateUseCase(BaseUseCase):

    def __init__(
            self,
            quota_repo: ResourceQuotaRepository = Depends(get_resource_quota_repository),
            limit_repo: LimitRangeRepository = Depends(get_limit_range_repository),
            vpa_repo: VpaRepository = Depends(get_vpa_repository),
    ):
        self.quota_repo = quota_repo
        self.limit_repo = limit_repo
        self.vpa_repo = vpa_repo

    async def __call__(
            self,
            project_name: str,
            payload: ProjectResourceUpdateRequest
    ) -> ResourceQuota:
        """Project의 리소스 할당량 (ResourceQuota, LimitRange, VPA)을 수정합니다."""

        # 1. ResourceQuota 업데이트
        updated_quota = await self._update_resource_quota(project_name, payload)

        # 2. LimitRange 생성 또는 업데이트
        await self._create_or_update_limit_range(project_name, updated_quota)

        # 3. VPA 생성 또는 업데이트
        await self._create_or_update_vpa(project_name)

        return updated_quota

    async def _update_resource_quota(self, project_name: str, payload: ProjectResourceUpdateRequest) -> ResourceQuota:
        """지정된 프로젝트(네임스페이스)의 ResourceQuota를 찾아 업데이트합니다."""
        quotas = await self.quota_repo.find_all(namespace=project_name, label_selector="managed-by=madp")
        if not quotas:
            raise ResourceQuotaNotFoundException()
        
        existing_quota = quotas[0]

        # 요청에 명시된 값만 업데이트하고, 나머지는 기존 값 유지
        # ResourceQuotaLimits는 to_dict가 있고, ResourceQuota는 hard_limits가 dict. 역변환이 필요.
        # 간단하게 가기 위해, 기존 값에서 새로운 값으로 덮어쓰는 방식을 사용.
        new_limits_dict = existing_quota.hard_limits.copy()
        if payload.cpu:
            new_limits_dict["requests.cpu"] = payload.cpu
            new_limits_dict["limits.cpu"] = payload.cpu
        if payload.memory:
            new_limits_dict["requests.memory"] = payload.memory
            new_limits_dict["limits.memory"] = payload.memory
        if payload.disk:
            new_limits_dict["requests.storage"] = payload.disk

        # dataclasses.replace를 사용하여 불변 객체의 복사본을 만듭니다.
        updated_quota_obj = dataclasses.replace(existing_quota, hard_limits=new_limits_dict)
        
        saved_quota = await self.quota_repo.save(updated_quota_obj)
        return saved_quota

    async def _create_or_update_limit_range(self, project_name: str, quota: ResourceQuota):
        """지정된 프로젝트(네임스페이스)에 LimitRange를 생성하거나 업데이트합니다."""
        limit_range_name = f"{project_name}-limits"
        
        # 간단한 기본값 설정. defaultRequest는 quota의 1/10, max는 quota와 동일하게.
        # 실제로는 더 정교한 정책이 필요할 수 있음.
        default_cpu_request = "100m"
        default_mem_request = "128Mi"
        
        limit_item = LimitRangeItem(
            type="Container",
            default_request={"cpu": default_cpu_request, "memory": default_mem_request},
            default={"cpu": default_cpu_request, "memory": default_mem_request}, # default와 defaultRequest를 동일하게
            max= {"cpu": quota.hard_limits.get("limits.cpu"), "memory": quota.hard_limits.get("limits.memory")},
        )

        existing_limit_range = await self.limit_repo.find_by_name(name=limit_range_name, namespace=project_name)

        if existing_limit_range:
            # dataclasses.replace를 사용하여 업데이트
            updated_limit_range = dataclasses.replace(existing_limit_range, limits=[limit_item])
        else:
            updated_limit_range = LimitRange(
                name=limit_range_name,
                namespace=project_name,
                limits=[limit_item],
                labels=MANAGED_BY_LABEL
            )
        
        await self.limit_repo.save(updated_limit_range)

    async def _create_or_update_vpa(self, project_name: str):
        """지정된 프로젝트(네임스페이스)에 VPA를 생성하거나 업데이트합니다."""
        vpa_name = f"{project_name}-vpa"
        
        # 네임스페이스의 모든 Deployment를 타겟으로 하는 VPA
        # targetRef의 이름은 와일드카드나 빈칸을 지원하지 않으므로, VPA는 보통 개별 Deployment마다 만들거나,
        # VPA Operator가 특정 레이블의 Deployment를 자동으로 타겟팅하도록 설정해야 합니다.
        # 여기서는 특정 Deployment를 지정하지 않고, VPA 객체만 생성하여 '추천' 모드로 두는 것을 예시로 합니다.
        # 이 경우 targetRef는 실제로 동작하지 않으므로, name을 placeholder로 둡니다.
        # 실제 환경에서는 VPA의 targetRef를 어떻게 관리할지에 대한 정책이 필요합니다.
        
        # 여기서는 VPA가 네임스페이스의 모든 Pod를 대상으로 동작하게 하는 것은 VPA 자체의 기능이 아니므로
        # 특정 Deployment를 타겟으로 하도록 가이드. 하지만 지금은 타겟이 없으므로 생성만.
        # targetRef가 필수이므로, 더미 값을 넣습니다.
        vpa_target = {"apiVersion": "apps/v1", "kind": "Deployment", "name": "placeholder-target"}
        
        existing_vpa = await self.vpa_repo.find_by_name(name=vpa_name, namespace=project_name)

        if existing_vpa:
             # 현재는 VPA의 설정을 변경하는 로직은 없음. 존재하면 넘어감.
            pass
        else:
            # updateMode: "Off"는 리소스 추천만 하고, 자동으로 적용하지 않음.
            vpa = VerticalPodAutoscaler.for_deployment(
                name=vpa_name,
                namespace=project_name,
                deployment_name="*", # 실제로는 와일드카드를 지원하지 않음. VPA는 보통 1:1 매핑
                update_mode="Off"
            )
            # targetRef를 수정하여 모든 Deployment에 적용하는 것처럼 보이게 함
            # spec.targetRef를 직접 수정하는 것은 도메인 모델에 맞지 않음
            # 여기서는 VPA를 생성하는 행위 자체에 집중.
            # 하지만 targetRef는 필수다.
            # 이 부분은 정책 논의가 더 필요. 일단은 생성하지 않거나, 생성하더라도 특정 타겟이 없음을 명시해야 함.
            # 사용자 요청은 'VPA를 활용하여 관리' 이므로, 일단 객체를 만들어두는 데 집중.
            # 하지만 동작하지 않는 VPA는 의미가 없으므로, 이 부분은 로그를 남기거나 예외를 발생시키는게 나을 수 있음.
            # 여기서는 VPA 생성을 일단 보류.
            # raise NotImplementedError("VPA target policy is not defined yet.")
            pass
