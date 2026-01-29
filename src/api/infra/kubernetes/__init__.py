from fastapi import APIRouter

from src.api.infra.kubernetes.namespace.endpoint import namespace_router
from src.api.infra.kubernetes.deployment.endpoint import deployment_router
from src.api.infra.kubernetes.service.endpoint import service_router
from src.api.infra.kubernetes.pod.endpoint import pod_router
from src.api.infra.kubernetes.resource_quota.endpoint import resource_quota_router
from src.api.infra.kubernetes.limit_range.endpoint import limit_range_router
from src.api.infra.kubernetes.configmap.endpoint import configmap_router
from src.api.infra.kubernetes.statefulset.endpoint import statefulset_router
from src.api.infra.kubernetes.job.endpoint import job_router
from src.api.infra.kubernetes.cronjob.endpoint import cronjob_router
from src.api.infra.kubernetes.pvc.endpoint import pvc_router

kubernetes_router = APIRouter(
    prefix="/kubernetes",
)

kubernetes_router.include_router(namespace_router)
kubernetes_router.include_router(deployment_router)
kubernetes_router.include_router(service_router)
kubernetes_router.include_router(pod_router)
kubernetes_router.include_router(resource_quota_router)
kubernetes_router.include_router(limit_range_router)
kubernetes_router.include_router(configmap_router)
kubernetes_router.include_router(statefulset_router)
kubernetes_router.include_router(job_router)
kubernetes_router.include_router(cronjob_router)
kubernetes_router.include_router(pvc_router)
