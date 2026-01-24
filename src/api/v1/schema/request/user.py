from fastapi import Header
from pydantic import BaseModel


class User(BaseModel):
    id : str = Header(alias="user-id")