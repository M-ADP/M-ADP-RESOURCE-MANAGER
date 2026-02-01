"""Proxmox 관련 예외 클래스 정의"""

from typing import Optional


class ProxmoxException(Exception):
    """Proxmox 관련 기본 예외"""

    def __init__(self, message: str, detail: Optional[dict] = None):
        self.message = message
        self.detail = detail or {}
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (detail: {self.detail})"


class ProxmoxConnectionException(ProxmoxException):
    """Proxmox 연결 실패 시 발생하는 예외"""

    def __init__(self, host: str, reason: str, detail: Optional[dict] = None):
        message = f"Proxmox 연결 실패: {host} - {reason}"
        super().__init__(message, detail)


class ProxmoxVMNotFoundException(ProxmoxException):
    """VM을 찾을 수 없을 때 발생하는 예외"""

    def __init__(self, node: str, vmid: int, detail: Optional[dict] = None):
        message = f"VM을 찾을 수 없습니다: node={node}, vmid={vmid}"
        enhanced_detail = detail or {}
        enhanced_detail.update({"node": node, "vmid": vmid})
        super().__init__(message, enhanced_detail)


class ProxmoxVMListException(ProxmoxException):
    """VM 목록 조회 실패 시 발생하는 예외"""

    def __init__(self, node: str, reason: str, detail: Optional[dict] = None):
        message = f"VM 목록 조회 실패 [node={node}]: {reason}"
        enhanced_detail = detail or {}
        enhanced_detail.update({"node": node, "reason": reason})
        super().__init__(message, enhanced_detail)


class ProxmoxVMStatusException(ProxmoxException):
    """VM 상태 조회 실패 시 발생하는 예외"""

    def __init__(self, node: str, vmid: int, reason: str, detail: Optional[dict] = None):
        message = f"VM 상태 조회 실패 [node={node}, vmid={vmid}]: {reason}"
        enhanced_detail = detail or {}
        enhanced_detail.update({"node": node, "vmid": vmid, "reason": reason})
        super().__init__(message, enhanced_detail)


class ProxmoxVMMetricsException(ProxmoxException):
    """VM 메트릭 조회 실패 시 발생하는 예외"""

    def __init__(self, node: str, vmid: int, timeframe: str, reason: str, detail: Optional[dict] = None):
        message = f"VM 메트릭 조회 실패 [node={node}, vmid={vmid}, timeframe={timeframe}]: {reason}"
        enhanced_detail = detail or {}
        enhanced_detail.update({"node": node, "vmid": vmid, "timeframe": timeframe, "reason": reason})
        super().__init__(message, enhanced_detail)
