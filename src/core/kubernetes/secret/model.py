from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class Secret:
    """Kubernetes Secret 도메인 객체

    Note: RMS는 Secret 값을 직접 관리하지 않고,
    Vault 연동을 통한 Secret 접근 구조만 관리합니다.
    """

    name: str
    namespace: str
    secret_type: str = "Opaque"  # Opaque, kubernetes.io/service-account-token, etc.
    data: Dict[str, str] = field(default_factory=dict)  # base64 encoded
    string_data: Dict[str, str] = field(default_factory=dict)  # plain text
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def with_data(self, key: str, value: str) -> "Secret":
        """새로운 데이터가 추가된 Secret 반환 (base64 encoded)"""
        return Secret(
            name=self.name,
            namespace=self.namespace,
            secret_type=self.secret_type,
            data={**self.data, key: value},
            string_data=self.string_data,
            labels=self.labels,
            annotations=self.annotations,
        )

    def with_string_data(self, key: str, value: str) -> "Secret":
        """새로운 문자열 데이터가 추가된 Secret 반환"""
        return Secret(
            name=self.name,
            namespace=self.namespace,
            secret_type=self.secret_type,
            data=self.data,
            string_data={**self.string_data, key: value},
            labels=self.labels,
            annotations=self.annotations,
        )

    def with_labels(self, labels: Dict[str, str]) -> "Secret":
        """새로운 레이블이 추가된 Secret 반환"""
        return Secret(
            name=self.name,
            namespace=self.namespace,
            secret_type=self.secret_type,
            data=self.data,
            string_data=self.string_data,
            labels={**self.labels, **labels},
            annotations=self.annotations,
        )
