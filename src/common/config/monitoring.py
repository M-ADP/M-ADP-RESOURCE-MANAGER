"""Monitoring 설정"""

from pydantic_settings import BaseSettings


class MonitoringConfig(BaseSettings):
    """모니터링 임계값 설정
    
    환경변수:
        MONITORING_THRESHOLD_CPU: CPU 할당률 임계값 (%, 기본 80)
        MONITORING_THRESHOLD_MEMORY: Memory 할당률 임계값 (%, 기본 80)
        MONITORING_THRESHOLD_STORAGE: Storage 할당률 임계값 (%, 기본 80)
    """
    
    threshold_cpu: int = 80
    threshold_memory: int = 80
    threshold_storage: int = 80
    
    class Config:
        env_prefix = "MONITORING_"
