from fastapi import FastAPI

from app.bootstrap import router
from app.bootstrap.exception import register_exception_handlers


def create_app():
    app = FastAPI()

    # 예외 핸들러 등록
    register_exception_handlers(app)

    return app