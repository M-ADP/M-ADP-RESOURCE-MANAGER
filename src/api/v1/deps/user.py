from fastapi import Header

from src.core.user.model import User


def get_user(user_id: str = Header(alias="user-id")) -> User:
    return User(id=user_id)