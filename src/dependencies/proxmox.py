from proxmoxer import ProxmoxAPI

from src.core.config.proxmox import PROXMOX_CONFIG
from src.core.proxmox.client import ProxmoxClient
from src.infra.proxmox.client import ProxmoxClientImpl

_proxmox_client: ProxmoxClient | None = None


def get_proxmox_client() -> ProxmoxClient:
    global _proxmox_client

    if _proxmox_client is None:
        api = ProxmoxAPI(
            host=PROXMOX_CONFIG.PROXMOX_HOST,
            port=PROXMOX_CONFIG.PROXMOX_PORT,
            user=PROXMOX_CONFIG.PROXMOX_TOKEN_ID,
            token_name=PROXMOX_CONFIG.PROXMOX_TOKEN_NAME,
            token_value=PROXMOX_CONFIG.PROXMOX_TOKEN_SECRET,
            verify_ssl=PROXMOX_CONFIG.PROXMOX_VERIFY_SSL,
        )
        _proxmox_client = ProxmoxClientImpl(api=api)

    return _proxmox_client
