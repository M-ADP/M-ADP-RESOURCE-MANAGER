from typing import TypeVar, Generic, Optional
from pydantic import BaseModel

T = TypeVar('T')




class SuccessResponse(BaseModel, Generic[T]):
    """API 성공 응답 모델"""
    message: str
    data: T


class ErrorResponse(BaseModel):
    """API 예외 응답 모델"""
    message: str