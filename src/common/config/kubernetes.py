from typing import Optional
from pydantic_settings import BaseSettings

class KubernetesConfig(BaseSettings):
    """Kubernetes 클라이언트 설정"""

    # Kubeconfig 파일 경로 (None이면 in-cluster 또는 기본 경로)
    kubeconfig_path: Optional[str] = None

    # In-cluster 설정 사용 여부
    use_in_cluster_config: bool = False

    # API 서버 URL (직접 지정 시)
    api_server_url: Optional[str] = None

    # 네임스페이스 기본값
    default_namespace: str = "default"

    # API 타임아웃 (초)
    api_timeout: int = 60

    # 재시도 횟수
    max_retries: int = 3

    class Config:
        env_prefix = "K8S_"  # 환경변수 접두사: K8S_KUBECONFIG_PATH 등
