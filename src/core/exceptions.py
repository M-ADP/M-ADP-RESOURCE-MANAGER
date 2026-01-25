from enum import Enum


class ExceptionDetail(str, Enum):
    # Not Found
    NAMESPACE_NOT_FOUND = "Namespace not found"
    SERVICE_NOT_FOUND = "Service not found"
    PORT_NOT_FOUND = "Port not found"
    RESOURCE_QUOTA_NOT_FOUND = "Resource quota not found"

    # Forbidden
    FORBIDDEN = "Forbidden"

    # Conflict
    SERVICE_ALREADY_EXISTS = "Service already exists"


class MadpException(Exception):
    def __init__(self, detail: ExceptionDetail):
        self.detail = detail
        super().__init__(self.detail.value)


class NotFoundException(MadpException):
    def __init__(self, detail: ExceptionDetail):
        if self.__class__ is NotFoundException:
            raise NotImplementedError("This is an abstract exception. You should inherit it.")
        super().__init__(detail)


class ForbiddenException(MadpException):
    def __init__(self, detail: ExceptionDetail):
        if self.__class__ is ForbiddenException:
            raise NotImplementedError("This is an abstract exception. You should inherit it.")
        super().__init__(detail)


class ConflictException(MadpException):
    def __init__(self, detail: ExceptionDetail):
        if self.__class__ is ConflictException:
            raise NotImplementedError("This is an abstract exception. You should inherit it.")
        super().__init__(detail)


class NamespaceNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__(detail=ExceptionDetail.NAMESPACE_NOT_FOUND)


class ServiceNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__(detail=ExceptionDetail.SERVICE_NOT_FOUND)


class PortNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__(detail=ExceptionDetail.PORT_NOT_FOUND)


class ResourceQuotaNotFoundException(NotFoundException):
    def __init__(self):
        super().__init__(detail=ExceptionDetail.RESOURCE_QUOTA_NOT_FOUND)


class ServiceAlreadyExistsException(ConflictException):
    def __init__(self):
        super().__init__(detail=ExceptionDetail.SERVICE_ALREADY_EXISTS)
