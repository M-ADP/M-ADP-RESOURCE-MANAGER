from fastapi import Header

from src.core.user.model import User


def get_user(user_id: str = Header(alias="X-User-Id")) -> User:
    return User(id=user_id)