from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class ProjectId:
    """프로젝트 ID 값 객체"""

    id: str

    @property
    def namespace(self) -> str:
        """Kubernetes 네임스페이스 이름 (project-{id})"""
        return f"project-{self.id}"


@dataclass(frozen=True)
class Project:
    """프로젝트 도메인 객체"""

    id: str
    name: str
    user_id: str
    cpu: str = "100m"
    memory: str = "32Mi"
    disk: str = "32Mi"

    # save 후 채워지는 결과 필드
    resource_quota_id: str = ""
    limits: Dict[str, str] = field(default_factory=dict)

    @property
    def namespace(self) -> str:
        """Kubernetes 네임스페이스 이름 — ProjectId 기반으로 결정론적 도출"""
        return ProjectId(self.id).namespace

    def with_result(self, resource_quota_id: str, limits: Dict[str, str]) -> "Project":
        return Project(
            id=self.id,
            name=self.name,
            user_id=self.user_id,
            cpu=self.cpu,
            memory=self.memory,
            disk=self.disk,
            resource_quota_id=resource_quota_id,
            limits=limits,
        )
