from fastapi import FastAPI

from app.bootstrap import router


def create_app():
    app = FastAPI()
    return app