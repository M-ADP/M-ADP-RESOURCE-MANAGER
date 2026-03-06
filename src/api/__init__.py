from fastapi import FastAPI


def create_app():
    from src.api.exception_handler import register_exception_handlers
    from src.api.routers import register_routers
    from src.api.lifespan import lifespan

    app = FastAPI(lifespan=lifespan)

    # 예외 핸들러 등록
    register_exception_handlers(app)
    register_routers(app)

    return app
