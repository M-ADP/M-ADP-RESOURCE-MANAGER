from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PersistentVolumeClaim:
    """Kubernetes PersistentVolumeClaim 도메인 객체"""

    name: str
    namespace: str
    storage_class_name: Optional[str] = None
    access_modes: List[str] = field(default_factory=lambda: ["ReadWriteOnce"])
    storage: str = "1Gi"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    volume_mode: str = "Filesystem"  # Filesystem or Block
    selector: Optional[Dict[str, str]] = None
    phase: Optional[str] = None  # Pending, Bound, Lost

    def with_storage(self, storage: str) -> "PersistentVolumeClaim":
        """스토리지 크기가 변경된 PVC 반환"""
        return PersistentVolumeClaim(
            name=self.name,
            namespace=self.namespace,
            storage_class_name=self.storage_class_name,
            access_modes=self.access_modes,
            storage=storage,
            labels=self.labels,
            annotations=self.annotations,
            volume_mode=self.volume_mode,
            selector=self.selector,
            phase=self.phase,
        )

    def with_labels(self, labels: Dict[str, str]) -> "PersistentVolumeClaim":
        """새로운 레이블이 추가된 PVC 반환"""
        return PersistentVolumeClaim(
            name=self.name,
            namespace=self.namespace,
            storage_class_name=self.storage_class_name,
            access_modes=self.access_modes,
            storage=self.storage,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            volume_mode=self.volume_mode,
            selector=self.selector,
            phase=self.phase,
        )
