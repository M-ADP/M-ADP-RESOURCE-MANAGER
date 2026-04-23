from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class KubernetesConfig(BaseSettings):
    """Kubernetes 클라이언트 설정"""

    model_config = SettingsConfigDict(
        env_prefix="K8S_",
        extra="ignore",
        env_file="/vault/secrets/.env",
        env_file_encoding="utf-8",
    )

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

    # RMS 파드의 ServiceAccount 이름 (project namespace에 RoleBinding 생성 시 사용)
    service_account_name: str = "resource-manager"
    service_account_namespace: str = "madp"

    # project namespace에 부여할 ClusterRole 이름
    pvc_cluster_role_name: str = "resource-manager-pvc-manager"

    # Watch 설정 (기본 비활성 — 수평 확장 환경에서 인스턴스 하나만 켤 것)
    watch_enabled: bool = True
    watch_namespace_prefix: str = "project-"
    watch_failure_ttl_seconds: int = 3600
    watch_performops_url: Optional[str] = None  # e.g. "http://orchestrator:8000"
