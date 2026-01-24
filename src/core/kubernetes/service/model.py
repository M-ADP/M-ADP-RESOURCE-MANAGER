from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ServicePort:
    """Kubernetes Service Port 정의"""

    port: int
    target_port: int
    protocol: str = "TCP"
    name: Optional[str] = None
    node_port: Optional[int] = None


@dataclass(frozen=True)
class Service:
    """Kubernetes Service 도메인 객체"""

    name: str
    namespace: str
    ports: List[ServicePort] = field(default_factory=list)
    selector: Dict[str, str] = field(default_factory=dict)
    service_type: str = "ClusterIP"  # ClusterIP, NodePort, LoadBalancer
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    cluster_ip: Optional[str] = None
    external_ips: List[str] = field(default_factory=list)

    def with_port(self, port: ServicePort) -> "Service":
        """새로운 포트가 추가된 Service 반환"""
        return Service(
            name=self.name,
            namespace=self.namespace,
            ports=[*self.ports, port],
            selector=self.selector,
            service_type=self.service_type,
            labels=self.labels,
            annotations=self.annotations,
            cluster_ip=self.cluster_ip,
            external_ips=self.external_ips,
        )

    def with_labels(self, labels: Dict[str, str]) -> "Service":
        """새로운 레이블이 추가된 Service 반환"""
        return Service(
            name=self.name,
            namespace=self.namespace,
            ports=self.ports,
            selector=self.selector,
            service_type=self.service_type,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            cluster_ip=self.cluster_ip,
            external_ips=self.external_ips,
        )
