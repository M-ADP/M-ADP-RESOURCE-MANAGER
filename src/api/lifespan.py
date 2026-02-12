
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.core.logger import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리"""
    logger.info("Application starting up...")
    yield
    logger.info("Application shutting down...")
