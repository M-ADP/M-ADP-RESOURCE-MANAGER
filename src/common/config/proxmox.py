import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class ProxmoxConfig(BaseSettings):
    PROXMOX_HOST : str
    PROXMOX_TOKEN_ID : str
    PROXMOX_TOKEN_SECRET : str
    PROXMOX_TOKEN_NAME : str
    PROXMOX_PORT : int
    PROXMOX_VERIFY_SSL : bool = False


PROXMOX_CONFIG = ProxmoxConfig()