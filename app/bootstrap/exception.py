from fastapi import Request, status, FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from core.response import ErrorResponse
from core.exception import AppException
from core.logger import log_error


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """AppException 핸들러 - 예상 가능한 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.message).model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP 예외 핸들러"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.detail).model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """요청 검증 예외 핸들러"""
    errors = exc.errors()
    error_messages = []

    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(message=", ".join(error_messages)).model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """예상치 못한 예외 핸들러"""

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(message="서버 내부 오류가 발생했습니다.").model_dump()
    )


def register_exception_handlers(app: FastAPI) -> None:
    """예외 핸들러 등록"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
