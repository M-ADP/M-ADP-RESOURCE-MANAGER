from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.kubernetes.hpa.model import HorizontalPodAutoscaler


@dataclass(frozen=True)
class Volume:
    """Kubernetes Volume 정의"""

    name: str
    pvc_name: Optional[str] = None  # PVC 볼륨인 경우


@dataclass(frozen=True)
class SecurityContext:
    """Kubernetes SecurityContext 정의"""

    privileged: Optional[bool] = None
    run_as_non_root: Optional[bool] = None
    allow_privilege_escalation: Optional[bool] = None
    read_only_root_filesystem: Optional[bool] = None
    capabilities_add: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Container:
    """Kubernetes Container 정의"""

    name: str
    image: str
    ports: List[Dict[str, Any]] = field(default_factory=list)
    env: List[Dict[str, Any]] = field(default_factory=list)
    resources: Optional[Dict[str, Any]] = None
    security_context: Optional[SecurityContext] = None
    volume_mounts: List[Dict[str, Any]] = field(default_factory=list)
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None


@dataclass(frozen=True)
class DeploymentStatus:
    """Kubernetes Deployment 상태"""

    replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    available_replicas: Optional[int] = None
    updated_replicas: Optional[int] = None


@dataclass(frozen=True)
class Deployment:
    """Kubernetes Deployment 도메인 객체"""

    name: str
    namespace: str
    replicas: int = 1
    containers: List[Container] = field(default_factory=list)
    volumes: List[Volume] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    selector_labels: Dict[str, str] = field(default_factory=dict)
    security_context: Optional[SecurityContext] = None
    service_account_name: Optional[str] = None
    image_pull_secrets: List[str] = field(default_factory=list)
    status: Optional[DeploymentStatus] = None

    # ── Naming convention properties ─────────────────────────────────────────

    @property
    def hpa_name(self) -> str:
        """이 Deployment와 연결된 HPA 이름"""
        return f"{self.name}-hpa"

    @property
    def sa_name(self) -> str:
        """이 Deployment와 연결된 ServiceAccount 이름"""
        return f"{self.name}-sa"

    @property
    def env_configmap_name(self) -> str:
        """이 Deployment의 환경변수 ConfigMap 이름"""
        return f"{self.name}-env"

    @property
    def vault_policy_name(self) -> str:
        """이 Deployment와 연결된 Vault Policy 이름"""
        return f"{self.namespace}-{self.name}-policy"

    @property
    def vault_role_name(self) -> str:
        """이 Deployment와 연결된 Vault Kubernetes Auth Role 이름"""
        return f"{self.namespace}-{self.name}-role"

    @property
    def vault_secret_name(self) -> str:
        """이 Deployment의 고정 Vault Secret 이름"""
        return "app-secret"

    def vault_secret_path(self, secret_name: str | None = None) -> str:
        """이 Deployment의 Vault Secret 경로"""
        return f"{self.namespace}/{self.name}/{secret_name or self.vault_secret_name}"

    def vault_secrets_prefix(self) -> str:
        """이 Deployment의 Vault Secret 목록 조회용 prefix"""
        return f"{self.namespace}/{self.name}/"

    # ── Builders ─────────────────────────────────────────────────────────────

    def with_replicas(self, replicas: int) -> "Deployment":
        """레플리카 수가 변경된 Deployment 반환"""
        return Deployment(
            name=self.name,
            namespace=self.namespace,
            replicas=replicas,
            containers=self.containers,
            labels=self.labels,
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            service_account_name=self.service_account_name,
            status=self.status,
        )

    def with_labels(self, labels: Dict[str, str]) -> "Deployment":
        """새로운 레이블이 추가된 Deployment 반환"""
        return Deployment(
            name=self.name,
            namespace=self.namespace,
            replicas=self.replicas,
            containers=self.containers,
            volumes=self.volumes,
            labels={**self.labels, **labels},
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            service_account_name=self.service_account_name,
            status=self.status,
        )

    def with_container_resources(
        self,
        container_name: str,
        requests: Optional[Dict[str, str]] = None,
        limits: Optional[Dict[str, str]] = None,
    ) -> "Deployment":
        """특정 컨테이너의 리소스가 변경된 Deployment 반환"""
        new_containers = []
        for c in self.containers:
            if c.name == container_name:
                current = c.resources or {}
                new_resources = {**current}
                if requests is not None:
                    new_resources["requests"] = {
                        **(current.get("requests") or {}),
                        **requests,
                    }
                if limits is not None:
                    new_resources["limits"] = {
                        **(current.get("limits") or {}),
                        **limits,
                    }
                new_containers.append(
                    Container(
                        name=c.name,
                        image=c.image,
                        ports=c.ports,
                        env=c.env,
                        resources=new_resources,
                        volume_mounts=c.volume_mounts,
                        command=c.command,
                        args=c.args,
                    )
                )
            else:
                new_containers.append(c)
        return Deployment(
            name=self.name,
            namespace=self.namespace,
            replicas=self.replicas,
            containers=new_containers,
            volumes=self.volumes,
            labels=self.labels,
            annotations=self.annotations,
            selector_labels=self.selector_labels,
            service_account_name=self.service_account_name,
            status=self.status,
        )

    def create_hpa(
        self,
        min_replicas: int = 1,
        max_replicas: int = 10,
        target_cpu_utilization: int = 80,
        target_memory_utilization: Optional[int] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> "HorizontalPodAutoscaler":
        """이 Deployment를 대상으로 하는 HPA 도메인 객체 생성"""
        from src.core.kubernetes.hpa.model import HorizontalPodAutoscaler

        return HorizontalPodAutoscaler.for_deployment(
            deployment=self,
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            target_cpu_utilization=target_cpu_utilization,
            target_memory_utilization=target_memory_utilization,
            labels=labels,
        )
