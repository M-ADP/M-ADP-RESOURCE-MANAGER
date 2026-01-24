from abc import ABC
from typing import Optional

from kubernetes.client import CoreV1Api
from kubernetes_asyncio.client import ApiClient, RbacAuthorizationV1Api, AppsV1Api, BatchV1Api

from src.core.config.kubernetes import KubernetesConfig
from src.core.logger import Logger


class KubernetesClient(ABC):

    def __init__(self, k8s_config: KubernetesConfig, logger: Logger):
        # config
        self.config = k8s_config

        # logger
        self.logger = logger

        # kubernetes
        self.api_client: Optional[ApiClient] = None
        self.core_v1: Optional[CoreV1Api] = None
        self.apps_v1: Optional[AppsV1Api] = None
        self.rbac_v1: Optional[RbacAuthorizationV1Api] = None
        self.batch_v1: Optional[BatchV1Api] = None



