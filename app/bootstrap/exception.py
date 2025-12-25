from fastapi import Request, status, FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from core.response import ErrorResponse
from core.exception import AppException
from core.logger import get_logger

# 로거 인스턴스 가져오기
logger = get_logger()


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """AppException 핸들러 - 예상 가능한 예외 처리"""
    logger.error(request, exc, exc.status_code, exc.message)

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.message).model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP 예외 핸들러"""
    logger.error(request, exc, exc.status_code, exc.detail)

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

    error_message = ", ".join(error_messages)
    logger.error(request, exc, status.HTTP_422_UNPROCESSABLE_ENTITY, error_message)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(message=error_message).model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """예상치 못한 예외 핸들러"""
    logger.error(request, exc, status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))

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
