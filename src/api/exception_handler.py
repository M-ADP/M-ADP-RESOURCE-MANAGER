from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from src.core.exceptions import NotFoundException, ForbiddenException, MadpException




def register_exception_handlers(app: FastAPI):
    @app.exception_handler(MadpException)
    async def madp_exception_handler(request: Request, exc: MadpException):
        return JSONResponse(
            status_code=400,
            content={"detail": exc.detail.value},
        )

    @app.exception_handler(NotFoundException)
    async def not_found_exception_handler(request: Request, exc: NotFoundException):
        return JSONResponse(
            status_code=404,
            content={"detail": exc.detail.value},
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
        return JSONResponse(
            status_code=403,
            content={"detail": exc.detail.value},
        )