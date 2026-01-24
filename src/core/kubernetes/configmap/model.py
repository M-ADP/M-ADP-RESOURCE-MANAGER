from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class ConfigMap:
    """Kubernetes ConfigMap 도메인 객체"""

    name: str
    namespace: str
    data: Dict[str, str] = field(default_factory=dict)
    binary_data: Optional[Dict[str, bytes]] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def with_data(self, key: str, value: str) -> "ConfigMap":
        """새로운 데이터가 추가된 ConfigMap 반환"""
        return ConfigMap(
            name=self.name,
            namespace=self.namespace,
            data={**self.data, key: value},
            binary_data=self.binary_data,
            labels=self.labels,
            annotations=self.annotations,
        )

    def with_labels(self, labels: Dict[str, str]) -> "ConfigMap":
        """새로운 레이블이 추가된 ConfigMap 반환"""
        return ConfigMap(
            name=self.name,
            namespace=self.namespace,
            data=self.data,
            binary_data=self.binary_data,
            labels={**self.labels, **labels},
            annotations=self.annotations,
        )
