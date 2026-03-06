from src.infra.vault.client import VaultClient

def get_vault_client() -> VaultClient:
    return VaultClient()
