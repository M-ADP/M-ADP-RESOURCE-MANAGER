from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from src.core import (
    BadRequestException,
    NotFoundException,
    ForbiddenException,
    ConflictException,
    TooManyRequestsException,
    InternalServerException,
)
from src.infra.kubernetes import KubernetesResourceException
from src.infra.proxmox import ProxmoxException


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(BadRequestException)
    async def bad_request_handler(request: Request, exc: BadRequestException):
        return JSONResponse(status_code=400, content={"detail": exc.detail})

    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException):
        return JSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(ForbiddenException)
    async def forbidden_handler(request: Request, exc: ForbiddenException):
        return JSONResponse(status_code=403, content={"detail": exc.detail})

    @app.exception_handler(ConflictException)
    async def conflict_handler(request: Request, exc: ConflictException):
        return JSONResponse(status_code=409, content={"detail": exc.detail})

    @app.exception_handler(TooManyRequestsException)
    async def too_many_requests_handler(request: Request, exc: TooManyRequestsException):
        return JSONResponse(status_code=429, content={"detail": exc.detail})

    @app.exception_handler(InternalServerException)
    async def internal_server_handler(request: Request, exc: InternalServerException):
        return JSONResponse(status_code=500, content={"detail": exc.detail})

    @app.exception_handler(KubernetesResourceException)
    async def k8s_resource_handler(request: Request, exc: KubernetesResourceException):
        return JSONResponse(status_code=500, content={"detail": exc.detail})

    @app.exception_handler(ProxmoxException)
    async def proxmox_resource_handler(request: Request, exc: ProxmoxException):
        return JSONResponse(status_code=500, content={"detail": exc.detail})

