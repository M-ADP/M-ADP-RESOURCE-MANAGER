"""MADP 예외 정의 - 도메인 규약

HTTP 상태코드 기반 상위 예외만 정의합니다.
구체적인 예외는 각 모듈에서 이 클래스들을 상속하여 정의합니다.
"""
from abc import ABC


class MadpException(Exception):
    """MADP 기본 예외"""
    detail: str = "Internal server error"

    def __init__(self, detail: str = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class BadRequestException(MadpException, ABC):
    """400 Bad Request"""
    detail = "Bad request"


class NotFoundException(MadpException, ABC):
    """404 Not Found"""
    detail = "Not found"


class ForbiddenException(MadpException, ABC):
    """403 Forbidden"""
    detail = "Forbidden"


class ConflictException(MadpException, ABC):
    """409 Conflict"""
    detail = "Conflict"


class TooManyRequestsException(MadpException, ABC):
    """429 Too Many Requests"""
    detail = "Too many requests"


class InternalServerException(MadpException, ABC):
    """500 Internal Server Error"""
    detail = "Internal server error"
