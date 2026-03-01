"""Service 관련 예외"""

from src.core import NotFoundException, ConflictException


class ServiceNotFoundException(NotFoundException):
    """Service 미발견"""
    detail = "Service not found"


class PortNotFoundException(NotFoundException):
    """Port 미발견"""
    detail = "Port not found"


class ServiceAlreadyExistsException(ConflictException):
    """Service 이미 존재"""
    detail = "Service already exists"
