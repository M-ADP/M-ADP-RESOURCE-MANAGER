from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TlsConfig:
    """Gateway TLS 설정"""

    mode: str = "SIMPLE"  # SIMPLE, MUTUAL, PASSTHROUGH, etc.
    credential_name: Optional[str] = None
    min_protocol_version: Optional[str] = None
    max_protocol_version: Optional[str] = None


@dataclass(frozen=True)
class GatewayPort:
    """Gateway Server Port 정의"""

    number: int
    name: str
    protocol: str = "HTTP"  # HTTP, HTTPS, GRPC, HTTP2, MONGO, TCP, TLS


@dataclass(frozen=True)
class GatewayServer:
    """Gateway Server 정의 (포트 + 호스트 + TLS)"""

    port: GatewayPort
    hosts: List[str] = field(default_factory=lambda: ["*"])
    tls: Optional[TlsConfig] = None

    def with_hosts(self, hosts: List[str]) -> "GatewayServer":
        """호스트가 변경된 GatewayServer 반환"""
        return GatewayServer(
            port=self.port,
            hosts=hosts,
            tls=self.tls,
        )

    def with_tls(self, tls: TlsConfig) -> "GatewayServer":
        """TLS 설정이 추가된 GatewayServer 반환"""
        return GatewayServer(
            port=self.port,
            hosts=self.hosts,
            tls=tls,
        )


@dataclass(frozen=True)
class Gateway:
    """Kubernetes/Istio Gateway 도메인 객체"""

    name: str
    namespace: str
    servers: List[GatewayServer] = field(default_factory=list)
    selector: Dict[str, str] = field(default_factory=lambda: {"istio": "ingressgateway"})
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def for_port(
        cls,
        name: str,
        namespace: str,
        port: int,
        protocol: str = "HTTP",
        hosts: Optional[List[str]] = None,
    ) -> "Gateway":
        """특정 포트를 위한 Gateway 생성 헬퍼"""
        server = GatewayServer(
            port=GatewayPort(
                number=port,
                name=f"{protocol.lower()}-{port}",
                protocol=protocol,
            ),
            hosts=hosts or ["*"],
        )
        return cls(
            name=name,
            namespace=namespace,
            servers=[server],
        )

    @classmethod
    def for_project_port(
        cls,
        project_name: str,
        port: int,
        protocol: str = "HTTP",
        hosts: Optional[List[str]] = None,
    ) -> "Gateway":
        """프로젝트의 특정 포트를 위한 Gateway 생성 헬퍼"""
        gateway_name = f"{project_name}-gateway"
        return cls.for_port(
            name=gateway_name,
            namespace=project_name,
            port=port,
            protocol=protocol,
            hosts=hosts,
        )

    def with_server(self, server: GatewayServer) -> "Gateway":
        """새로운 서버가 추가된 Gateway 반환"""
        return Gateway(
            name=self.name,
            namespace=self.namespace,
            servers=[*self.servers, server],
            selector=self.selector,
            labels=self.labels,
            annotations=self.annotations,
        )

    def with_selector(self, selector: Dict[str, str]) -> "Gateway":
        """셀렉터가 변경된 Gateway 반환"""
        return Gateway(
            name=self.name,
            namespace=self.namespace,
            servers=self.servers,
            selector={**self.selector, **selector},
            labels=self.labels,
            annotations=self.annotations,
        )

    def with_labels(self, labels: Dict[str, str]) -> "Gateway":
        """레이블이 추가된 Gateway 반환"""
        return Gateway(
            name=self.name,
            namespace=self.namespace,
            servers=self.servers,
            selector=self.selector,
            labels={**self.labels, **labels},
            annotations=self.annotations,
        )

    def update_server_hosts_by_port(self, port_number: int, new_hosts: List[str]) -> "Gateway":
        """포트 번호로 서버를 찾아 호스트를 업데이트하고, 새 Gateway 객체를 반환합니다."""
        updated_servers = []
        found = False
        for server in self.servers:
            if server.port.number == port_number:
                updated_servers.append(server.with_hosts(new_hosts))
                found = True
            else:
                updated_servers.append(server)
        
        if not found:
            return self

        return Gateway(
            name=self.name,
            namespace=self.namespace,
            servers=updated_servers,
            selector=self.selector,
            labels=self.labels,
            annotations=self.annotations,
        )
