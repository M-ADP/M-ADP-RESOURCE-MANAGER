import os

from pydantic_settings import BaseSettings


class ProxmoxConfig(BaseSettings):
    HOST : str
    TOKEN_ID : str
    TOKEN_SECRET : str
    TOKEN_NAME : str
    VERIFY_SSL : bool = False
