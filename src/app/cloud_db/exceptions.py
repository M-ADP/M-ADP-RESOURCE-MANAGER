"""Cloud DB 관련 예외"""

from src.core.exceptions import NotFoundException, BadRequestException


class CloudDbNotFoundException(NotFoundException):
    """CloudDb(StatefulSet) 미발견"""
    detail = "CloudDb not found"

    def __init__(self, name: str, namespace: str):
        super().__init__(f"CloudDb '{name}' not found in namespace '{namespace}'")


class CloudDbContainerNotFoundException(NotFoundException):
    """Container 미발견"""
    detail = "Container not found"

    def __init__(self, name: str = None):
        if name:
            super().__init__(f"No containers found in cloud_db '{name}'")
        else:
            super().__init__("No containers found in cloud_db")


class CloudDbPvcNotFoundException(NotFoundException):
    """PVC 미발견"""
    detail = "PVC not found"

    def __init__(self, name: str, namespace: str):
        super().__init__(f"PVC '{name}' not found in namespace '{namespace}'. Disk was not configured for this container.")


class CloudDbDiskReductionNotAllowedException(BadRequestException):
    """Disk 축소 불가"""
    detail = "Disk reduction is not allowed"

    def __init__(self, current: str, requested: str):
        super().__init__(f"Disk size can only be increased. Current: {current}, Requested: {requested}")


class CloudDbConfigMapNotFoundException(NotFoundException):
    """ConfigMap 미발견"""
    detail = "ConfigMap not found"

    def __init__(self, name: str, namespace: str):
        super().__init__(f"ConfigMap '{name}' not found in namespace '{namespace}'")
