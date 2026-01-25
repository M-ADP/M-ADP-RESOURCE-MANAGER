from abc import ABC, abstractmethod
from typing import List, Optional

from .model import Namespace


class NamespaceRepository(ABC):
    """Namespace Repository 추상 인터페이스"""
    
    @abstractmethod
    async def save(self, namespace: Namespace) -> Namespace:
        """
        Namespace 저장 (생성 또는 업데이트, 멱등성 보장)
        
        Args:
            namespace: 저장할 Namespace 도메인 객체
            
        Returns:
            저장된 Namespace 도메인 객체
        """
        ...
    
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[Namespace]:
        """
        ID로 Namespace 조회
        
        Args:
            id: Namespace ID
            
        Returns:
            Namespace 도메인 객체, 없으면 None
        """
        ...
    
    @abstractmethod
    async def find_all(
        self,
        label_selector: Optional[str] = None,
    ) -> List[Namespace]:
        """
        Namespace 목록 조회
        
        Args:
            label_selector: 레이블 셀렉터 (예: "env=production")
            
        Returns:
            Namespace 도메인 객체 목록
        """
        ...
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Namespace 삭제
        
        Args:
            id: Namespace ID
            
        Returns:
            삭제 성공 여부
        """
        ...
    
    @abstractmethod
    async def exists(self, id: str) -> bool:
        """
        Namespace 존재 여부 확인
        
        Args:
            id: Namespace ID
            
        Returns:
            존재 여부
        """
        ...
