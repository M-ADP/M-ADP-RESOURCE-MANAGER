import logging
import sys
from typing import Optional
from fastapi import Request

from core.config.logger import LoggerConfig


class Logger:
    """애플리케이션 로거 클래스"""

    def __init__(self, config: LoggerConfig):
        self.config = config
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """로거 설정 및 초기화"""
        logger = logging.getLogger(self.config.logger_name)
        logger.setLevel(self.config.log_level)

        # 기존 핸들러 제거 (중복 방지)
        logger.handlers.clear()

        # 포맷터 설정
        formatter = logging.Formatter(
            fmt=self.config.log_format,
            datefmt=self.config.log_date_format
        )

        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.config.log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 파일 핸들러 추가 (설정된 경우)
        if self.config.enable_file_logging and self.config.log_file_path:
            file_handler = logging.FileHandler(self.config.log_file_path)
            file_handler.setLevel(self.config.log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def error(
        self,
        request: Request,
        exc: Exception,
        status_code: int,
        message: Optional[str] = None
    ) -> None:
        """에러 로그 기록"""
        error_message = message or str(exc)

        self.logger.error(
            f"[{status_code}] {request.method} {request.url.path} - {error_message}",
            exc_info=True,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
            }
        )

    def info(self, message: str) -> None:
        """정보 로그 기록"""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """경고 로그 기록"""
        self.logger.warning(message)

    def debug(self, message: str) -> None:
        """디버그 로그 기록"""
        self.logger.debug(message)


# 싱글톤 패턴으로 전역 로거 인스턴스 생성
_logger_instance: Optional[Logger] = None


def get_logger() -> Logger:
    """로거 인스턴스 반환 (의존성 주입용)"""
    global _logger_instance

    if _logger_instance is None:
        config = LoggerConfig()
        _logger_instance = Logger(config)

    return _logger_instance
