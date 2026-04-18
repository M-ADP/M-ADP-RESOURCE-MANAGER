"""Node 리소스 관리 클래스"""

import json
import time
from typing import Optional, List, Dict, Tuple
from kubernetes_asyncio.client import V1Node
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from src.common.util.unit_converter import UnitConverter
from .exceptions import NodeReadException, NodeListException

_STATS_CACHE: Dict[str, Tuple[float, dict]] = {}  # {node_name: (timestamp, data)}
_CACHE_TTL = 30.0


class NodeManager:
    """Node 리소스를 관리하는 클래스 (읽기 전용)
    
    Node는 클러스터 레벨 리소스로, 이 매니저는 조회 기능만 제공합니다.
    CLAUDE.md에 따라 Node 생성/삭제/업데이트는 관리하지 않습니다.
    """

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def list_nodes(
        self,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1Node]:
        """클러스터의 모든 Node 목록 조회
        
        Args:
            label_selector: 레이블 셀렉터 (예: "node-role.kubernetes.io/worker=")
            field_selector: 필드 셀렉터 (예: "spec.unschedulable=false")
        
        Returns:
            V1Node 객체 리스트
        
        Raises:
            NodeListException: 목록 조회 실패 시
        """
        try:
            result = await self.k8s_client.core_v1.list_node(
                label_selector=label_selector,
                field_selector=field_selector,
            )
            return result.items
        
        except ApiException as e:
            self.logger.logger.error(f"Node 목록 조회 실패 - {e.reason}")
            raise NodeListException(
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )
        
        except Exception as e:
            self.logger.logger.error(f"Node 목록 조회 중 예외 발생 - {str(e)}")
            raise NodeListException(reason=str(e))

    async def get_node(self, name: str) -> Optional[V1Node]:
        """특정 Node 조회
        
        Args:
            name: Node 이름
        
        Returns:
            V1Node 객체 또는 None
        
        Raises:
            NodeReadException: 조회 실패 시 (404 제외)
        """
        try:
            node = await self.k8s_client.core_v1.read_node(name=name)
            return node
        
        except ApiException as e:
            if e.status == 404:
                return None
            
            self.logger.logger.error(f"Node 조회 실패: {name} - {e.reason}")
            raise NodeReadException(
                node_name=name,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )
        
        except Exception as e:
            self.logger.logger.error(f"Node 조회 중 예외 발생: {name} - {str(e)}")
            raise NodeReadException(node_name=name, reason=str(e))

    async def get_node_volume_stats(self, node_name: str) -> dict:
        """kubelet stats/summary API로 노드의 Pod 볼륨 사용량 조회 (30초 캐시)

        Returns:
            kubelet stats summary 원본 dict. 실패 시 빈 dict.
        """
        cached = _STATS_CACHE.get(node_name)
        if cached:
            cached_at, data = cached
            if time.monotonic() - cached_at < _CACHE_TTL:
                return data

        try:
            response = await self.k8s_client.core_v1.connect_get_node_proxy_with_path(
                node_name, "stats/summary"
            )
            data = json.loads(response) if isinstance(response, str) else response
            _STATS_CACHE[node_name] = (time.monotonic(), data)
            return data
        except Exception as e:
            self.logger.warning(f"Node stats 조회 실패: {node_name} - {e}")
            return {}

    async def get_cluster_allocatable_resources(self) -> Dict[str, int]:
        """클러스터 전체 할당 가능한 리소스 합계 조회
        
        모든 노드의 allocatable 리소스를 합산하여 반환합니다.
        
        Returns:
            {
                "cpu_millicores": int,      # 총 CPU (밀리코어)
                "memory_bytes": int,         # 총 메모리 (바이트)
                "storage_bytes": int,        # 총 임시 스토리지 (바이트)
            }
        
        Raises:
            NodeListException: 노드 목록 조회 실패 시
        """
        nodes = await self.list_nodes()
        
        total_cpu_millicores = 0
        total_memory_bytes = 0
        total_storage_bytes = 0
        
        for node in nodes:
            if node.status and node.status.allocatable:
                allocatable = node.status.allocatable
                
                # CPU
                if "cpu" in allocatable:
                    total_cpu_millicores += UnitConverter.parse_cpu_to_millicores(
                        allocatable["cpu"]
                    )
                
                # Memory
                if "memory" in allocatable:
                    total_memory_bytes += UnitConverter.parse_storage_to_bytes(
                        allocatable["memory"]
                    )
                
                # Ephemeral Storage
                if "ephemeral-storage" in allocatable:
                    total_storage_bytes += UnitConverter.parse_storage_to_bytes(
                        allocatable["ephemeral-storage"]
                    )
        
        return {
            "cpu_millicores": total_cpu_millicores,
            "memory_bytes": total_memory_bytes,
            "storage_bytes": total_storage_bytes,
        }
