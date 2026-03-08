from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectId:
    """프로젝트 ID 값 객체"""

    id: str

    @property
    def namespace(self) -> str:
        """Kubernetes 네임스페이스 이름 (project-{id})"""
        return f"project-{self.id}"
