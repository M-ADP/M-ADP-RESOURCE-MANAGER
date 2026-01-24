
from fastapi import APIRouter

from src.api.v1.project.endpoint import project_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(project_router)