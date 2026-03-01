"""Monitoring 관련 예외 클래스"""

from src.core.exceptions import MadpException


class MonitoringException(MadpException):
    """모니터링 관련 기본 예외"""
    detail = "Monitoring error"


class ClusterResourceCalculationException(MonitoringException):
    """클러스터 리소스 계산 실패 시 발생하는 예외"""
    
    def __init__(self, reason: str):
        super().__init__(detail=f"클러스터 리소스 계산 실패: {reason}")
