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

    def with_target_port(self, new_target_port: int) -> "ServicePort":
        """target_port가 변경된 ServicePort 반환"""
        return ServicePort(
            port=self.port,
            target_port=new_target_port,
            protocol=self.protocol,
            name=self.name,
            node_port=self.node_port,
        )
    
    def with_protocol(self, new_protocol: str) -> "ServicePort":
        """protocol이 변경된 ServicePort 반환"""
        return ServicePort(
            port=self.port,
            target_port=self.target_port,
            protocol=new_protocol,
            name=self.name,
            node_port=self.node_port,
        )


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

    def with_annotations(self, annotations: Dict[str, str]) -> "Service":
        """새로운 어노테이션이 추가된 Service 반환"""
        return Service(
            name=self.name,
            namespace=self.namespace,
            ports=self.ports,
            selector=self.selector,
            service_type=self.service_type,
            labels=self.labels,
            annotations={**self.annotations, **annotations},
            cluster_ip=self.cluster_ip,
            external_ips=self.external_ips,
        )

    def with_selector(self, selector: Dict[str, str]) -> "Service":
        """selector가 변경된 Service 반환"""
        return Service(
            name=self.name,
            namespace=self.namespace,
            ports=self.ports,
            selector=selector,
            service_type=self.service_type,
            labels=self.labels,
            annotations=self.annotations,
            cluster_ip=self.cluster_ip,
            external_ips=self.external_ips,
        )

    def with_service_type(self, service_type: str) -> "Service":
        """service_type이 변경된 Service 반환"""
        return Service(
            name=self.name,
            namespace=self.namespace,
            ports=self.ports,
            selector=self.selector,
            service_type=service_type,
            labels=self.labels,
            annotations=self.annotations,
            cluster_ip=self.cluster_ip,
            external_ips=self.external_ips,
        )

    def update_port_by_number(
        self,
        port_number: int,
        new_target_port: Optional[int] = None,
        new_protocol: Optional[str] = None,
    ) -> "Service":
        """포트 번호로 ServicePort를 찾아 target_port 또는 protocol을 업데이트한 새 Service 객체를 반환합니다."""
        updated_ports = []
        found = False
        for service_port in self.ports:
            if service_port.port == port_number:
                updated_port = service_port
                if new_target_port is not None:
                    updated_port = updated_port.with_target_port(new_target_port)
                if new_protocol is not None:
                    updated_port = updated_port.with_protocol(new_protocol)
                updated_ports.append(updated_port)
                found = True
            else:
                updated_ports.append(service_port)

        if not found:
            return self # 일치하는 포트가 없으면 원본 Service 반환

        return Service(
            name=self.name,
            namespace=self.namespace,
            ports=updated_ports,
            selector=self.selector,
            service_type=self.service_type,
            labels=self.labels,
            annotations=self.annotations,
            cluster_ip=self.cluster_ip,
            external_ips=self.external_ips,
        )
