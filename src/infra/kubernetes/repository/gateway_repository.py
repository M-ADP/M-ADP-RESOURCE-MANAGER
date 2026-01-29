from typing import List, Optional, Any, Dict
import dataclasses

from src.core.kubernetes.gateway import Gateway, GatewayRepository, GatewayServer, GatewayPort, TlsConfig
from src.infra.kubernetes.managers.gateway import IstioGatewayManager


class K8sGatewayRepository(GatewayRepository):
    """Kubernetes Gateway Repository 구현체"""

    def __init__(self, manager: IstioGatewayManager):
        self._manager = manager

    async def save(self, gateway: Gateway) -> Gateway:
        """Gateway 저장 (생성 또는 업데이트, 멱등성 보장)"""

        def to_dict(obj):
            if dataclasses.is_dataclass(obj):
                return dataclasses.asdict(obj)
            return obj

        servers_dict = [to_dict(server) for server in gateway.servers]
        
        raw_gateway = await self._manager.create_gateway(
            name=gateway.name,
            namespace=gateway.namespace,
            servers=servers_dict,
            selector=gateway.selector,
            labels=gateway.labels,
            annotations=gateway.annotations,
        )
        return self._to_domain(raw_gateway)

    async def find_by_name(self, name: str, namespace: str) -> Optional[Gateway]:
        """이름과 네임스페이스로 Gateway 조회"""
        raw_gateway = await self._manager.get_gateway(name, namespace)
        if raw_gateway is None:
            return None
        return self._to_domain(raw_gateway)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Gateway]:
        """Gateway 목록 조회"""
        raw_gateways = await self._manager.list_gateways(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(gw) for gw in raw_gateways]

    async def delete(self, name: str, namespace: str) -> bool:
        """Gateway 삭제"""
        return await self._manager.delete_gateway(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        """Gateway 존재 여부 확인"""
        return await self._manager.exists(name, namespace)

    def _to_domain(self, raw_gateway: Dict[str, Any]) -> Gateway:
        """Kubernetes API 응답(dict)을 도메인 객체로 변환"""
        metadata = raw_gateway.get("metadata", {})
        spec = raw_gateway.get("spec", {})
        
        servers = []
        for server_data in spec.get("servers", []):
            port_data = server_data.get("port", {})
            tls_data = server_data.get("tls")
            
            servers.append(GatewayServer(
                port=GatewayPort(
                    number=port_data.get("number"),
                    name=port_data.get("name"),
                    protocol=port_data.get("protocol"),
                ),
                hosts=server_data.get("hosts", []),
                tls=TlsConfig(
                    mode=tls_data.get("mode"),
                    credential_name=tls_data.get("credentialName"),
                ) if tls_data else None
            ))

        return Gateway(
            name=metadata.get("name"),
            namespace=metadata.get("namespace"),
            servers=servers,
            selector=spec.get("selector", {}),
            labels=metadata.get("labels", {}),
            annotations=metadata.get("annotations", {}),
        )

