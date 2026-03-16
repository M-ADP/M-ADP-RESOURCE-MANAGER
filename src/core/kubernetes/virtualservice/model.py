from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class VirtualServiceDestination:
    """VirtualService HTTP 라우트의 목적지"""

    host: str        # Kubernetes Service 이름
    port: int        # 서비스 포트 번호
    weight: int = 100


@dataclass(frozen=True)
class VirtualServiceHttpRoute:
    """VirtualService HTTP 라우팅 규칙"""

    destinations: List[VirtualServiceDestination]


@dataclass(frozen=True)
class VirtualService:
    """Istio VirtualService 도메인 객체"""

    name: str
    namespace: str
    hosts: List[str]                         # 라우팅 대상 호스트명 목록
    gateways: List[str]                      # 연결할 Gateway 이름 목록
    http_routes: List[VirtualServiceHttpRoute]
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
