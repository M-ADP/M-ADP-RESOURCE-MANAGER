from proxmoxer import ProxmoxAPI

from src.core.config.proxmox import ProxmoxConfig
from src.core.proxmox.client import ProxmoxClient
from src.infra.proxmox.client import ProxmoxClientImpl

async def get_proxmox(

):

    def create_proxmox() -> ProxmoxClient:

        api = ProxmoxAPI(
            host=ProxmoxConfig.HOST,
            user=ProxmoxConfig.TOKEN_ID,
            token_name=ProxmoxConfig.TOKEN_NAME,
            token_value=ProxmoxConfig.TOKEN_SECRET,
            verify_ssl=ProxmoxConfig.VERIFY_SSL,
        )

        return ProxmoxClientImpl(api=api)
