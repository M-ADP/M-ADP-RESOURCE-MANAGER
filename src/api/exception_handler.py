from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    BadRequestException,
    NotFoundException,
    ForbiddenException,
    ConflictException,
    TooManyRequestsException,
    InternalServerException,
)


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
