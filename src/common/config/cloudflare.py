from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudflareConfig(BaseSettings):
    """Cloudflare DNS/Tunnel 설정 (Vault env 주입 기반)"""

    model_config = SettingsConfigDict(
        env_prefix="CF_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

    api_token: str = ""
    zone_id: str = ""
    tunnel_id: str = ""
    account_id: str = ""
    gateway_url: str = ""
    base_domain: str = "example.com"
    proxied: bool = True
    ttl: int = 1  # 1 = Cloudflare automatic
