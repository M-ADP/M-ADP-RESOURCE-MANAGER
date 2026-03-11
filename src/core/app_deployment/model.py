"""App Deployment 도메인 모델"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AppContainerDisk:
    """앱 컨테이너 디스크(PVC) 설정"""

    size: str
    mount_path: str
    storage_class: str


@dataclass(frozen=True)
class AppContainer:
    """앱 컨테이너 스펙"""

    name: str
    image: str        # 원본 이미지 경로 (예: project_id/app_id:tag)
    harbor_url: str   # Harbor 레지스트리 URL
    ports: List[int] = field(default_factory=list)
    resources: Optional[Dict[str, Any]] = None
    env: Dict[str, str] = field(default_factory=dict)
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    disk: Optional[AppContainerDisk] = None

    @property
    def full_image(self) -> str:
        """Harbor URL이 포함된 전체 이미지 경로.

        예: harbor.harbor.svc.cluster.local/247003216871424/1164771540:20260310225455
        """
        prefix = f"{self.harbor_url}/"
        if self.image.startswith(prefix):
            return self.image
        return f"{prefix}{self.image}"


@dataclass(frozen=True)
class AppDeployment:
    """App Deployment 도메인 객체 (애플리케이션 배포 단위)"""

    name: str
    namespace: str
    containers: List[AppContainer]
    replicas: int = 1
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
