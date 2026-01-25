from fastapi import FastAPI

from src.api.exception_handler import register_exception_handlers
from src.api.routers import register_routers


def create_app():
    app = FastAPI()

    # 예외 핸들러 등록
    register_exception_handlers(app)
    register_routers(app)

    return app
