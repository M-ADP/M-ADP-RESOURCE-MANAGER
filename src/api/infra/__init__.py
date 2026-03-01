from fastapi import APIRouter

from src.api.infra.proxmox.endpoint import proxmox_router
from src.api.infra.kubernetes import kubernetes_router

infra_router = APIRouter(
    prefix="/infra",
)

infra_router.include_router(proxmox_router)
infra_router.include_router(kubernetes_router)
