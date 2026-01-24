from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class Namespace:
    """Kubernetes Namespace 도메인 객체"""
    
    name: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    status: Optional[str] = None  # Active, Terminating
    
    @classmethod
    def for_project(cls, user_id: str, project_name: str) -> "Namespace":
        """Creates a Namespace for a project with a standardized name."""
        name = f"{user_id}-{project_name}"
        return cls(name=name)

    def with_label(self, key: str, value: str) -> "Namespace":
        """새로운 레이블이 추가된 Namespace 반환 (불변성 유지)"""
        return Namespace(
            name=self.name,
            labels={**self.labels, key: value},
            annotations=self.annotations,
            status=self.status,
        )
    
    def with_labels(self, labels: Dict[str, str]) -> "Namespace":
        """여러 레이블이 추가된 Namespace 반환 (불변성 유지)"""
        return Namespace(
            name=self.name,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            status=self.status,
        )
    
    def with_annotation(self, key: str, value: str) -> "Namespace":
        """새로운 어노테이션이 추가된 Namespace 반환 (불변성 유지)"""
        return Namespace(
            name=self.name,
            labels=self.labels,
            annotations={**self.annotations, key: value},
            status=self.status,
        )
