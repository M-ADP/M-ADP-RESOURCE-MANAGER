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
        """단일 키-값이 추가/덮어쓰기된 ConfigMap 반환"""
        return ConfigMap(
            name=self.name,
            namespace=self.namespace,
            data={**self.data, key: value},
            binary_data=self.binary_data,
            labels=self.labels,
            annotations=self.annotations,
        )

    def merge_data(self, data: Dict[str, str]) -> "ConfigMap":
        """데이터를 병합한 ConfigMap 반환 (기존 키 유지, 새 키 추가/덮어쓰기)"""
        return ConfigMap(
            name=self.name,
            namespace=self.namespace,
            data={**self.data, **data},
            binary_data=self.binary_data,
            labels=self.labels,
            annotations=self.annotations,
        )

    def replace_data(self, data: Dict[str, str]) -> "ConfigMap":
        """데이터를 완전 교체한 ConfigMap 반환"""
        return ConfigMap(
            name=self.name,
            namespace=self.namespace,
            data=data,
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
