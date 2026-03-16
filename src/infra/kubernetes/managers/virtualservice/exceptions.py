from typing import Any, Dict, Optional


class VirtualServiceCreationException(Exception):
    def __init__(self, name: str, namespace: str, reason: str, detail: Optional[Dict[str, Any]] = None):
        self.name = name
        self.namespace = namespace
        self.reason = reason
        self.detail = detail or {}
        super().__init__(f"VirtualService 생성 실패: {name} (namespace: {namespace}) - {reason}")


class VirtualServiceReadException(Exception):
    def __init__(self, name: str, namespace: str, reason: str, detail: Optional[Dict[str, Any]] = None):
        self.name = name
        self.namespace = namespace
        self.reason = reason
        self.detail = detail or {}
        super().__init__(f"VirtualService 조회 실패: {name} (namespace: {namespace}) - {reason}")


class VirtualServiceDeletionException(Exception):
    def __init__(self, name: str, namespace: str, reason: str, detail: Optional[Dict[str, Any]] = None):
        self.name = name
        self.namespace = namespace
        self.reason = reason
        self.detail = detail or {}
        super().__init__(f"VirtualService 삭제 실패: {name} (namespace: {namespace}) - {reason}")
