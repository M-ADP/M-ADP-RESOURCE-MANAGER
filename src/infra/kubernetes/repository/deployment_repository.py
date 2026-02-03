from typing import Dict, List, Optional

from kubernetes_asyncio.client import (
    V1Deployment,
    V1Container,
    V1Volume,
    V1PersistentVolumeClaimVolumeSource,
    V1ContainerPort,
    V1EnvVar,
    V1ResourceRequirements,
    V1VolumeMount,
)

from src.core.kubernetes.deployment import Deployment, Container, DeploymentStatus, DeploymentRepository, Volume
from src.infra.kubernetes.managers.deployment import DeploymentManager


class K8sDeploymentRepository(DeploymentRepository):
    """Kubernetes Deployment Repository 구현체"""

    def __init__(self, manager: DeploymentManager):
        self._manager = manager

    async def save(self, deployment: Deployment) -> Deployment:
        containers = []
        for c in deployment.containers:
            # 포트 변환
            ports = None
            if c.ports:
                ports = [
                    V1ContainerPort(container_port=p.get("container_port"))
                    for p in c.ports
                ]

            # 환경 변수 변환
            env = None
            if c.env:
                env = [
                    V1EnvVar(name=e.get("name"), value=e.get("value"))
                    for e in c.env
                ]

            # 리소스 변환
            resources = None
            if c.resources:
                resources = V1ResourceRequirements(
                    requests=c.resources.get("requests"),
                    limits=c.resources.get("limits"),
                )

            # 볼륨 마운트 변환
            volume_mounts = None
            if c.volume_mounts:
                volume_mounts = [
                    V1VolumeMount(name=vm.get("name"), mount_path=vm.get("mount_path"))
                    for vm in c.volume_mounts
                ]

            containers.append(V1Container(
                name=c.name,
                image=c.image,
                ports=ports,
                env=env,
                resources=resources,
                volume_mounts=volume_mounts,
                command=c.command,
                args=c.args,
            ))
        volumes = None
        if deployment.volumes:
            volumes = [
                V1Volume(
                    name=v.name,
                    persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                        claim_name=v.pvc_name
                    ) if v.pvc_name else None,
                )
                for v in deployment.volumes
            ]
        v1_dep = await self._manager.create_deployment(
            name=deployment.name,
            namespace=deployment.namespace,
            containers=containers,
            replicas=deployment.replicas,
            labels=deployment.labels if deployment.labels else None,
            annotations=deployment.annotations if deployment.annotations else None,
            selector_labels=deployment.selector_labels if deployment.selector_labels else None,
            volumes=volumes,
            service_account_name=deployment.service_account_name,
        )
        return self._to_domain(v1_dep)

    async def find_by_name(self, name: str, namespace: str) -> Optional[Deployment]:
        v1_dep = await self._manager.get_deployment(name, namespace)
        if v1_dep is None:
            return None
        return self._to_domain(v1_dep)

    async def find_all(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Deployment]:
        v1_deps = await self._manager.list_deployments(
            namespace=namespace,
            label_selector=label_selector,
        )
        return [self._to_domain(d) for d in v1_deps]

    async def delete(self, name: str, namespace: str) -> bool:
        return await self._manager.delete_deployment(name, namespace)

    async def exists(self, name: str, namespace: str) -> bool:
        return await self._manager.exists(name, namespace)

    async def update_replicas(self, name: str, namespace: str, replicas: int) -> Deployment:
        v1_dep = await self._manager.update_replicas(name, namespace, replicas)
        return self._to_domain(v1_dep)

    async def update_container_resources(
        self,
        name: str,
        namespace: str,
        container_name: Optional[str] = None,
        requests: Optional[Dict[str, str]] = None,
        limits: Optional[Dict[str, str]] = None,
    ) -> Deployment:
        v1_dep = await self._manager.update_container_resources(
            name=name,
            namespace=namespace,
            container_name=container_name,
            requests=requests,
            limits=limits,
        )
        return self._to_domain(v1_dep)

    def _to_domain(self, v1_dep: V1Deployment) -> Deployment:
        containers = []
        volumes = []
        if v1_dep.spec and v1_dep.spec.template and v1_dep.spec.template.spec:
            for c in v1_dep.spec.template.spec.containers or []:
                # 리소스 추출
                resources = None
                if c.resources:
                    resources = {}
                    if c.resources.requests:
                        resources["requests"] = dict(c.resources.requests)
                    if c.resources.limits:
                        resources["limits"] = dict(c.resources.limits)

                # 볼륨 마운트 추출
                volume_mounts = []
                if c.volume_mounts:
                    for vm in c.volume_mounts:
                        volume_mounts.append({
                            "name": vm.name,
                            "mount_path": vm.mount_path,
                        })

                containers.append(Container(
                    name=c.name,
                    image=c.image,
                    resources=resources,
                    volume_mounts=volume_mounts,
                ))
            for v in v1_dep.spec.template.spec.volumes or []:
                pvc_name = None
                if v.persistent_volume_claim:
                    pvc_name = v.persistent_volume_claim.claim_name
                volumes.append(Volume(
                    name=v.name,
                    pvc_name=pvc_name,
                ))

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
            selector_labels=v1_dep.spec.selector.match_labels if v1_dep.spec and v1_dep.spec.selector else {},
            service_account_name=service_account_name,
            status=status,
        )
