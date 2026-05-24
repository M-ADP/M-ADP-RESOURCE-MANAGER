from pydantic_settings import BaseSettings, SettingsConfigDict


class IstioConfig(BaseSettings):
    """Istio 게이트웨이 설정"""

    model_config = SettingsConfigDict(
        env_prefix="ISTIO_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

    # 형식: "<namespace>/<gateway-name>", 예) "istio-ingress/ingressgateway"
    gateway_ref: str = "istio-ingress/ingressgateway"

    @property
    def gateway_namespace(self) -> str:
        return self.gateway_ref.split("/")[0]
