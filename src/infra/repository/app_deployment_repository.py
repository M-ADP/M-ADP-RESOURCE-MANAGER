"""AppDeployment 도메인 Repository K8s + Vault 구현체"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from kubernetes_asyncio.client import (
    V1Container,
    V1ContainerPort,
    V1Deployment,
    V1EnvVar,
    V1EnvFromSource,
    V1ConfigMapEnvSource,
    V1PersistentVolumeClaim,
    V1PersistentVolumeClaimVolumeSource,
    V1ResourceRequirements,
    V1ServiceAccount,
    V1Volume,
    V1VolumeMount,
    V2HorizontalPodAutoscaler,
)

from src.core.app_deployment import AppDeploymentRepository
from src.core.kubernetes.configmap import ConfigMap
from src.core.kubernetes.deployment import (
    Container,
    Deployment,
    DeploymentStatus,
    Volume,
)
from src.core.kubernetes.hpa import (
    HorizontalPodAutoscaler,
    HpaMetricSpec,
    HpaScaleTargetRef,
    HpaStatus,
)
from src.core.kubernetes.persistent_volume_claim import PersistentVolumeClaim
from src.core.kubernetes.pod import Event, Pod, PodLogs
from src.core.kubernetes.service_account import ServiceAccount
from src.infra.kubernetes.managers.configmap import ConfigMapManager
from src.infra.kubernetes.managers.deployment import DeploymentManager
from src.infra.kubernetes.managers.hpa import HpaManager
from src.infra.kubernetes.managers.persistentvolumeclaim import (
    PersistentVolumeClaimManager,
)
from src.infra.kubernetes.managers.pod import PodManager
from src.infra.kubernetes.managers.secret import SecretManager
from src.infra.kubernetes.managers.service_account import ServiceAccountManager
from src.infra.vault.client import VaultClient


class K8sAppDeploymentRepository(AppDeploymentRepository):
    """AppDeployment 도메인 Repository 구현체 (K8s + Vault)"""

    def __init__(
        self,
        deployment_manager: DeploymentManager,
        pvc_manager: PersistentVolumeClaimManager,
        service_account_manager: ServiceAccountManager,
        hpa_manager: HpaManager,
        pod_manager: PodManager,
        configmap_manager: ConfigMapManager,
        vault_client: VaultClient,
        secret_manager: SecretManager,
    ):
        self._deployment_manager = deployment_manager
        self._pvc_manager = pvc_manager
        self._service_account_manager = service_account_manager
        self._hpa_manager = hpa_manager
        self._pod_manager = pod_manager
        self._configmap_manager = configmap_manager
        self._vault_client = vault_client
        self._secret_manager = secret_manager

    # ── Deployment ──────────────────────────────────────────────────────────

    async def deploy(self, deployment: Deployment) -> Deployment:
        containers = [self._build_v1_container(c) for c in deployment.containers]

        existing = await self._deployment_manager.get_deployment(
            deployment.name, deployment.namespace
        )
        if existing:
            v1_dep = await self._deployment_manager.update_container_images(
                name=deployment.name,
                namespace=deployment.namespace,
                containers=containers,
                image_pull_secrets=deployment.image_pull_secrets or None,
            )
            return self._deployment_to_domain(v1_dep)

        volumes = None
        if deployment.volumes:
            volumes = [
                V1Volume(
                    name=v.name,
                    persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                        claim_name=v.pvc_name
                    )
                    if v.pvc_name
                    else None,
                )
                for v in deployment.volumes
            ]

        v1_dep = await self._deployment_manager.create_deployment(
            name=deployment.name,
            namespace=deployment.namespace,
            containers=containers,
            replicas=deployment.replicas,
            labels=deployment.labels or None,
            annotations=deployment.annotations or None,
            selector_labels=deployment.selector_labels or None,
            volumes=volumes,
            service_account_name=deployment.service_account_name,
            image_pull_secrets=deployment.image_pull_secrets or None,
        )
        return self._deployment_to_domain(v1_dep)

    async def find_deployment(self, name: str, namespace: str) -> Optional[Deployment]:
        v1_dep = await self._deployment_manager.get_deployment(name, namespace)
        if v1_dep is None:
            return None
        return self._deployment_to_domain(v1_dep)

    async def undeploy(self, deployment: Deployment) -> bool:
        return await self._deployment_manager.delete_deployment(
            deployment.name, deployment.namespace
        )

    async def scale(self, deployment: Deployment, replicas: int) -> Deployment:
        v1_dep = await self._deployment_manager.update_replicas(
            deployment.name, deployment.namespace, replicas
        )
        return self._deployment_to_domain(v1_dep)

    async def resize_container(
        self,
        deployment: Deployment,
        container_name: str,
        requests: Optional[Dict[str, str]] = None,
        limits: Optional[Dict[str, str]] = None,
    ) -> Deployment:
        v1_dep = await self._deployment_manager.update_container_resources(
            name=deployment.name,
            namespace=deployment.namespace,
            container_name=container_name,
            requests=requests,
            limits=limits,
        )
        return self._deployment_to_domain(v1_dep)

    # ── Storage (PVC) ────────────────────────────────────────────────────────

    async def provision_storage(
        self, pvc: PersistentVolumeClaim
    ) -> PersistentVolumeClaim:
        v1_pvc = await self._pvc_manager.create_pvc(
            name=pvc.name,
            namespace=pvc.namespace,
            storage_size=pvc.storage,
            storage_class_name=pvc.storage_class_name,
            access_modes=pvc.access_modes,
            labels=pvc.labels or None,
            annotations=pvc.annotations or None,
        )
        return self._pvc_to_domain(v1_pvc)

    async def find_storage(
        self, name: str, namespace: str
    ) -> Optional[PersistentVolumeClaim]:
        v1_pvc = await self._pvc_manager.get_pvc(name, namespace)
        if v1_pvc is None:
            return None
        return self._pvc_to_domain(v1_pvc)

    async def deprovision_storage(self, name: str, namespace: str) -> bool:
        return await self._pvc_manager.delete_pvc(name, namespace)

    async def expand_storage(
        self, pvc: PersistentVolumeClaim, new_size: str
    ) -> PersistentVolumeClaim:
        v1_pvc = await self._pvc_manager.resize_pvc(pvc.name, pvc.namespace, new_size)
        return self._pvc_to_domain(v1_pvc)

    # ── Identity (ServiceAccount) ────────────────────────────────────────────

    async def bind_identity(self, service_account: ServiceAccount) -> ServiceAccount:
        v1_sa = await self._service_account_manager.create_service_account(
            name=service_account.name,
            namespace=service_account.namespace,
            labels=service_account.labels or None,
            annotations=service_account.annotations or None,
            image_pull_secrets=service_account.image_pull_secrets or None,
        )
        return self._service_account_to_domain(v1_sa)

    async def unbind_identity(self, name: str, namespace: str) -> bool:
        return await self._service_account_manager.delete_service_account(
            name, namespace
        )

    # ── Autoscale (HPA) ──────────────────────────────────────────────────────

    async def enable_autoscale(
        self, hpa: HorizontalPodAutoscaler
    ) -> HorizontalPodAutoscaler:
        metrics = [
            {
                "type": m.type,
                "resource_name": m.resource_name,
                "target_type": m.target_type,
                "target_value": m.target_value,
            }
            for m in hpa.metrics
        ]
        raw_hpa = await self._hpa_manager.create_hpa(
            name=hpa.name,
            namespace=hpa.namespace,
            target_ref_name=hpa.scale_target_ref.name,
            target_ref_kind=hpa.scale_target_ref.kind,
            target_ref_api_version=hpa.scale_target_ref.api_version,
            min_replicas=hpa.min_replicas,
            max_replicas=hpa.max_replicas,
            metrics=metrics,
            labels=hpa.labels,
            annotations=hpa.annotations,
        )
        return self._hpa_to_domain(raw_hpa)

    async def disable_autoscale(self, deployment: Deployment) -> bool:
        return await self._hpa_manager.delete_hpa(
            deployment.hpa_name, deployment.namespace
        )

    # ── Observation (Pod) ────────────────────────────────────────────────────

    async def get_pods(self, deployment: Deployment) -> List[Pod]:
        v1_pods = await self._pod_manager.list_pods(
            namespace=deployment.namespace,
            label_selector=f"app_deployment={deployment.name}",
        )
        return [self._pod_to_domain(p) for p in v1_pods]

    async def get_pod_logs(
        self,
        pod_name: str,
        namespace: str,
        tail_lines: Optional[int] = None,
        since_seconds: Optional[int] = None,
        timestamps: bool = False,
    ) -> Optional[PodLogs]:
        logs = await self._pod_manager.get_pod_logs(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
            since_seconds=since_seconds,
            timestamps=timestamps,
        )
        if logs is None:
            return None
        return PodLogs(pod_name=pod_name, namespace=namespace, logs=logs)

    async def get_events(self, deployment: Deployment) -> List[Event]:
        result = await self._pod_manager.k8s_client.core_v1.list_namespaced_event(
            namespace=deployment.namespace,
        )
        events = []
        for event in result.items:
            obj = event.involved_object
            if obj.kind == "Deployment" and obj.name == deployment.name:
                events.append(self._event_to_domain(event))
            elif obj.kind == "ReplicaSet" and obj.name.startswith(
                f"{deployment.name}-"
            ):
                events.append(self._event_to_domain(event))
            elif obj.kind == "Pod" and obj.name.startswith(f"{deployment.name}-"):
                events.append(self._event_to_domain(event))

        _epoch = datetime.min.replace(tzinfo=timezone.utc)
        events.sort(
            key=lambda e: e.last_timestamp or e.first_timestamp or _epoch,
            reverse=True,
        )
        return events

    # ── Environment (ConfigMap) ──────────────────────────────────────────────

    async def set_env(
        self,
        deployment: Deployment,
        data: Dict[str, str],
        labels: Optional[Dict[str, str]] = None,
    ) -> ConfigMap:
        name = deployment.env_configmap_name
        namespace = deployment.namespace

        existing = await self._configmap_manager.get_configmap(
            name=name, namespace=namespace
        )
        if existing:
            v1_cm = await self._configmap_manager.update_data(
                name=name,
                namespace=namespace,
                data=data,
                merge=True,
            )
        else:
            v1_cm = await self._configmap_manager.create_configmap(
                name=name,
                namespace=namespace,
                data=data,
                labels=labels,
            )

        await self._ensure_env_from(deployment)

        return self._configmap_to_domain(v1_cm)

    async def replace_env(
        self, deployment: Deployment, data: Dict[str, str]
    ) -> ConfigMap:
        v1_cm = await self._configmap_manager.update_data(
            name=deployment.env_configmap_name,
            namespace=deployment.namespace,
            data=data,
            merge=False,
        )

        await self._ensure_env_from(deployment)

        return self._configmap_to_domain(v1_cm)

    async def replace_env(
        self, deployment: Deployment, data: Dict[str, str]
    ) -> ConfigMap:
        v1_cm = await self._configmap_manager.update_data(
            name=deployment.env_configmap_name,
            namespace=deployment.namespace,
            data=data,
            merge=False,
        )
        return self._configmap_to_domain(v1_cm)

    async def get_env(self, deployment: Deployment) -> Optional[ConfigMap]:
        v1_cm = await self._configmap_manager.get_configmap(
            name=deployment.env_configmap_name,
            namespace=deployment.namespace,
        )
        if v1_cm is None:
            return None
        return self._configmap_to_domain(v1_cm)

    async def clear_env(self, deployment: Deployment) -> bool:
        return await self._configmap_manager.delete_configmap(
            name=deployment.env_configmap_name,
            namespace=deployment.namespace,
        )

    async def _ensure_env_from(self, deployment: Deployment) -> None:
        existing = await self._deployment_manager.get_deployment(
            deployment.name, deployment.namespace
        )
        if not existing:
            return

        configmap_name = deployment.env_configmap_name
        containers = existing.spec.template.spec.containers or []

        env_froms = [
            V1EnvFromSource(config_map_ref=V1ConfigMapEnvSource(name=configmap_name))
        ]

        patch_containers = []
        for c in containers:
            patch_containers.append(
                {
                    "name": c.name,
                    "envFrom": [{"configMapRef": {"name": configmap_name}}],
                }
            )

        body = {"spec": {"template": {"spec": {"containers": patch_containers}}}}

        await self._deployment_manager.k8s_client.apps_v1.patch_namespaced_deployment(
            name=deployment.name,
            namespace=deployment.namespace,
            body=body,
        )

    # ── Secret (Vault) ───────────────────────────────────────────────────────

    @property
    def secret_mount_point(self) -> str:
        return self._vault_client.secret_mount_point

    async def store_secret(
        self,
        deployment: Deployment,
        data: Dict,
    ) -> str:
        secret_name = deployment.vault_secret_name
        secret_path = deployment.vault_secret_path(secret_name)
        await self._vault_client.patch_secret(path=secret_path, data=data)

        mount_point = self._vault_client.secret_mount_point
        policy_path = f"{mount_point}/data/{deployment.namespace}/{deployment.name}/*"
        policy_hcl = f'path "{policy_path}" {{\n  capabilities = ["read"]\n}}\n'
        await self._vault_client.create_policy(deployment.vault_policy_name, policy_hcl)

        await self._vault_client.create_kubernetes_role(
            role_name=deployment.vault_role_name,
            bound_service_account_names=[deployment.sa_name],
            bound_service_account_namespaces=[deployment.namespace],
            policies=[deployment.vault_policy_name],
        )

        await self._secret_manager.inject_vault_agent_to_deployment(
            deployment_name=deployment.name,
            namespace=deployment.namespace,
            vault_role=deployment.vault_role_name,
            secret_configs=[
                {
                    "name": secret_name,
                    "path": f"{mount_point}/data/{secret_path}",
                }
            ],
        )

        return f"{mount_point}/data/{secret_path}"

    async def list_app_secrets(self, deployment: Deployment) -> List[str]:
        return await self._vault_client.list_secrets(deployment.vault_secrets_prefix())

    async def revoke_secret(self, deployment: Deployment) -> bool:
        secret_name = deployment.vault_secret_name
        await self._vault_client.delete_secret(
            path=deployment.vault_secret_path(secret_name)
        )

        await self._vault_client.delete_kubernetes_role(deployment.vault_role_name)
        await self._vault_client.delete_policy(deployment.vault_policy_name)

        return True

    # ── 변환 헬퍼 ────────────────────────────────────────────────────────────

    def _build_v1_container(self, c: Container) -> V1Container:
        ports = None
        if c.ports:
            ports = [
                V1ContainerPort(container_port=p.get("container_port")) for p in c.ports
            ]

        env = None
        if c.env:
            env = [V1EnvVar(name=e.get("name"), value=e.get("value")) for e in c.env]

        resources = None
        if c.resources:
            resources = V1ResourceRequirements(
                requests=c.resources.get("requests"),
                limits=c.resources.get("limits"),
            )

        volume_mounts = None
        if c.volume_mounts:
            volume_mounts = [
                V1VolumeMount(name=vm.get("name"), mount_path=vm.get("mount_path"))
                for vm in c.volume_mounts
            ]

        return V1Container(
            name=c.name,
            image=c.image,
            ports=ports,
            env=env,
            resources=resources,
            volume_mounts=volume_mounts,
            command=c.command,
            args=c.args,
        )

    def _deployment_to_domain(self, v1_dep: V1Deployment) -> Deployment:
        containers = []
        volumes = []
        if v1_dep.spec and v1_dep.spec.template and v1_dep.spec.template.spec:
            for c in v1_dep.spec.template.spec.containers or []:
                resources = None
                if c.resources:
                    resources = {}
                    if c.resources.requests:
                        resources["requests"] = dict(c.resources.requests)
                    if c.resources.limits:
                        resources["limits"] = dict(c.resources.limits)

                volume_mounts = []
                if c.volume_mounts:
                    for vm in c.volume_mounts:
                        volume_mounts.append(
                            {
                                "name": vm.name,
                                "mount_path": vm.mount_path,
                            }
                        )

                containers.append(
                    Container(
                        name=c.name,
                        image=c.image,
                        resources=resources,
                        volume_mounts=volume_mounts,
                    )
                )

            for v in v1_dep.spec.template.spec.volumes or []:
                pvc_name = None
                if v.persistent_volume_claim:
                    pvc_name = v.persistent_volume_claim.claim_name
                volumes.append(Volume(name=v.name, pvc_name=pvc_name))

        status = None
        if v1_dep.status:
            status = DeploymentStatus(
                replicas=v1_dep.status.replicas,
                ready_replicas=v1_dep.status.ready_replicas,
                available_replicas=v1_dep.status.available_replicas,
                updated_replicas=v1_dep.status.updated_replicas,
            )

        service_account_name = None
        if v1_dep.spec and v1_dep.spec.template and v1_dep.spec.template.spec:
            service_account_name = v1_dep.spec.template.spec.service_account_name

        return Deployment(
            name=v1_dep.metadata.name,
            namespace=v1_dep.metadata.namespace,
            replicas=v1_dep.spec.replicas if v1_dep.spec else 1,
            containers=containers,
            volumes=volumes,
            labels=v1_dep.metadata.labels or {},
            annotations=v1_dep.metadata.annotations or {},
            selector_labels=v1_dep.spec.selector.match_labels
            if v1_dep.spec and v1_dep.spec.selector
            else {},
            service_account_name=service_account_name,
            status=status,
        )

    def _pvc_to_domain(self, v1_pvc: V1PersistentVolumeClaim) -> PersistentVolumeClaim:
        storage = "1Gi"
        if v1_pvc.spec and v1_pvc.spec.resources and v1_pvc.spec.resources.requests:
            storage = v1_pvc.spec.resources.requests.get("storage", "1Gi")
        return PersistentVolumeClaim(
            name=v1_pvc.metadata.name,
            namespace=v1_pvc.metadata.namespace,
            storage_class_name=v1_pvc.spec.storage_class_name if v1_pvc.spec else None,
            access_modes=v1_pvc.spec.access_modes if v1_pvc.spec else ["ReadWriteOnce"],
            storage=storage,
            labels=v1_pvc.metadata.labels or {},
            annotations=v1_pvc.metadata.annotations or {},
            volume_mode=v1_pvc.spec.volume_mode if v1_pvc.spec else "Filesystem",
            phase=v1_pvc.status.phase if v1_pvc.status else None,
        )

    def _service_account_to_domain(self, v1_sa: V1ServiceAccount) -> ServiceAccount:
        image_pull_secrets = []
        if v1_sa.image_pull_secrets:
            image_pull_secrets = [s.name for s in v1_sa.image_pull_secrets]
        return ServiceAccount(
            name=v1_sa.metadata.name,
            namespace=v1_sa.metadata.namespace,
            labels=v1_sa.metadata.labels or {},
            annotations=v1_sa.metadata.annotations or {},
            image_pull_secrets=image_pull_secrets,
        )

    def _hpa_to_domain(
        self, raw_hpa: V2HorizontalPodAutoscaler
    ) -> HorizontalPodAutoscaler:
        spec = raw_hpa.spec
        status = raw_hpa.status

        scale_target_ref = HpaScaleTargetRef(
            api_version=spec.scale_target_ref.api_version,
            kind=spec.scale_target_ref.kind,
            name=spec.scale_target_ref.name,
        )

        metrics = []
        if spec.metrics:
            for m in spec.metrics:
                if m.type == "Resource" and m.resource:
                    target_type = (
                        m.resource.target.type if m.resource.target else "Utilization"
                    )
                    target_value = (
                        m.resource.target.average_utilization
                        if target_type == "Utilization"
                        else m.resource.target.average_value
                    )
                    metrics.append(
                        HpaMetricSpec(
                            type="Resource",
                            resource_name=m.resource.name,
                            target_type=target_type,
                            target_value=int(target_value) if target_value else 0,
                        )
                    )

        hpa_status = None
        if status:
            current_cpu = None
            current_memory = None
            if status.current_metrics:
                for cm in status.current_metrics:
                    if cm.type == "Resource" and cm.resource:
                        if cm.resource.name == "cpu" and cm.resource.current:
                            current_cpu = cm.resource.current.average_utilization
                        elif cm.resource.name == "memory" and cm.resource.current:
                            current_memory = cm.resource.current.average_utilization
            hpa_status = HpaStatus(
                current_replicas=status.current_replicas,
                desired_replicas=status.desired_replicas,
                current_cpu_utilization=current_cpu,
                current_memory_utilization=current_memory,
            )

        return HorizontalPodAutoscaler(
            name=raw_hpa.metadata.name,
            namespace=raw_hpa.metadata.namespace,
            scale_target_ref=scale_target_ref,
            min_replicas=spec.min_replicas or 1,
            max_replicas=spec.max_replicas,
            metrics=metrics,
            labels=raw_hpa.metadata.labels or {},
            annotations=raw_hpa.metadata.annotations or {},
            status=hpa_status,
        )

    def _pod_to_domain(self, v1_pod) -> Pod:
        return Pod(
            name=v1_pod.metadata.name,
            namespace=v1_pod.metadata.namespace,
            phase=v1_pod.status.phase if v1_pod.status else None,
        )

    def _event_to_domain(self, v1_event) -> Event:
        return Event(
            type=v1_event.type or "Normal",
            reason=v1_event.reason or "",
            message=v1_event.message or "",
            involved_object_kind=v1_event.involved_object.kind,
            involved_object_name=v1_event.involved_object.name,
            first_timestamp=v1_event.first_timestamp,
            last_timestamp=v1_event.last_timestamp,
            count=v1_event.count,
        )

    def _configmap_to_domain(self, v1_cm) -> ConfigMap:
        return ConfigMap(
            name=v1_cm.metadata.name,
            namespace=v1_cm.metadata.namespace,
            data=v1_cm.data or {},
            labels=v1_cm.metadata.labels or {},
            annotations=v1_cm.metadata.annotations or {},
        )
