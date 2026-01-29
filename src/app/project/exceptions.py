"""Project 관련 예외"""

from src.core import BadRequestException, NotFoundException, ConflictException


class DiskReductionNotAllowedException(BadRequestException):
    """DISK 축소 불가"""
    detail = "Disk reduction is not allowed"

    def __init__(self, current: str, requested: str):
        self.current = current
        self.requested = requested
        super().__init__(f"Disk reduction is not allowed. Current: {current}, Requested: {requested}")


class ProjectNotFoundException(NotFoundException):
    """Project(Namespace) 미발견"""
    detail = "Project not found"


class ResourceQuotaNotFoundException(NotFoundException):
    """ResourceQuota 미발견"""
    detail = "Resource quota not found"


class ProjectAlreadyExistsException(ConflictException):
    """Project 이미 존재"""
    detail = "Project already exists"
