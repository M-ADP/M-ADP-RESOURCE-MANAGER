"""App 관련 예외"""

from src.core.exceptions import NotFoundException, BadRequestException


class DeploymentNotFoundException(NotFoundException):
    """Deployment 미발견"""
    detail = "Deployment not found"

    def __init__(self, name: str, namespace: str):
        super().__init__(f"Deployment '{name}' not found in namespace '{namespace}'")


class ContainerNotFoundException(NotFoundException):
    """Container 미발견"""
    detail = "Container not found"

    def __init__(self, deployment_name: str = None):
        if deployment_name:
            super().__init__(f"No containers found in deployment '{deployment_name}'")
        else:
            super().__init__("No containers found in deployment")


class PvcNotFoundException(NotFoundException):
    """PVC 미발견"""
    detail = "PVC not found"

    def __init__(self, name: str, namespace: str):
        super().__init__(f"PVC '{name}' not found in namespace '{namespace}'. Disk was not configured for this container.")


class DiskReductionNotAllowedException(BadRequestException):
    """Disk 축소 불가"""
    detail = "Disk reduction is not allowed"

    def __init__(self, current: str, requested: str):
        super().__init__(f"Disk size can only be increased. Current: {current}, Requested: {requested}")
