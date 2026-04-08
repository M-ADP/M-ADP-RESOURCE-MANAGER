"""Deployment 리소스 관리 클래스"""

import datetime
from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1Deployment,
    V1ObjectMeta,
    V1DeploymentSpec,
    V1DeploymentStrategy,
    V1LabelSelector,
    V1LocalObjectReference,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
    V1Volume,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    DeploymentCreationException,
    DeploymentReadException,
    DeploymentUpdateException,
    DeploymentDeletionException,
    DeploymentListException,
)


class DeploymentManager:
    """Deployment 리소스를 관리하는 클래스"""

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_deployment(
        self,
        name: str,
        namespace: str,
        containers: List[V1Container],
        replicas: int = 1,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        selector_labels: Optional[Dict[str, str]] = None,
        pod_labels: Optional[Dict[str, str]] = None,
        pod_annotations: Optional[Dict[str, str]] = None,
        volumes: Optional[List[V1Volume]] = None,
        service_account_name: Optional[str] = None,
        image_pull_secrets: Optional[List[str]] = None,
    ) -> V1Deployment:
        """Deployment 비동기 생성

        Args:
            name: Deployment 이름
            namespace: 네임스페이스
            containers: 컨테이너 리스트
            replicas: 레플리카 수
            labels: Deployment 레이블
            annotations: Deployment 어노테이션
            selector_labels: Pod 셀렉터 레이블 (None이면 labels 사용)
            pod_labels: Pod 레이블 (None이면 labels 사용)
            pod_annotations: Pod 어노테이션
            volumes: 볼륨 리스트 (PVC 마운트용)
            service_account_name: ServiceAccount 이름
            image_pull_secrets: 이미지 풀 시크릿 이름 리스트

        Returns:
            생성되거나 기존에 존재하는 V1Deployment 객체

        Raises:
            DeploymentCreationException: Deployment 생성 실패 시
        """
        self.logger.info(f"Deployment 생성 시도: {name} (namespace: {namespace})")

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_deployment(name, namespace)
        if existing:
            self.logger.info(f"Deployment 이미 존재함: {name} (namespace: {namespace})")
            return existing

        # 기본 레이블 설정
        deployment_labels = labels or {"app_deployment": name}
        selector_match_labels = selector_labels or deployment_labels
        pod_template_labels = pod_labels or deployment_labels

        # Deployment 객체 생성
        deployment = V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=deployment_labels,
                annotations=annotations or {},
            ),
            spec=V1DeploymentSpec(
                replicas=replicas,
                revision_history_limit=0,
                strategy=V1DeploymentStrategy(type="Recreate"),
                selector=V1LabelSelector(
                    match_labels=selector_match_labels,
                ),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(
                        labels=pod_template_labels,
                        annotations=pod_annotations or {},
                    ),
                    spec=V1PodSpec(
                        containers=containers,
                        volumes=volumes,
                        service_account_name=service_account_name,
                        image_pull_secrets=[
                            V1LocalObjectReference(name=s) for s in image_pull_secrets
                        ]
                        if image_pull_secrets
                        else None,
                    ),
                ),
            ),
        )

        try:
            dep = await self.k8s_client.apps_v1.create_namespaced_deployment(
                namespace=namespace,
                body=deployment,
            )
            self.logger.info(f"Deployment 생성 완료: {name} (namespace: {namespace})")
            return dep

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(f"Deployment 생성 충돌 (409), 재조회: {name}")
                existing = await self.get_deployment(name, namespace)
                if existing:
                    return existing

            self.logger.logger.error(
                f"Deployment 생성 실패: {name} - {e.reason} | body: {e.body}"
            )
            raise DeploymentCreationException(
                deployment_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(f"Deployment 생성 중 예외 발생: {name} - {str(e)}")
            raise DeploymentCreationException(
                deployment_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_deployment(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1Deployment]:
        """Deployment 비동기 조회

        Args:
            name: Deployment 이름
            namespace: 네임스페이스

        Returns:
            V1Deployment 객체 또는 None (존재하지 않으면)

        Raises:
            DeploymentReadException: 조회 실패 시 (404 제외)
        """
        try:
            dep = await self.k8s_client.apps_v1.read_namespaced_deployment(
                name=name,
                namespace=namespace,
            )
            return dep

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"Deployment 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise DeploymentReadException(
                deployment_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(f"Deployment 조회 중 예외 발생: {name} - {str(e)}")
            raise DeploymentReadException(
                deployment_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_deployment(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """Deployment 비동기 삭제

        Args:
            name: Deployment 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            DeploymentDeletionException: 삭제 실패 시
        """
        self.logger.info(f"Deployment 삭제 시도: {name} (namespace: {namespace})")

        # 존재 여부 확인
        existing = await self.get_deployment(name, namespace)
        if not existing:
            self.logger.warning(
                f"Deployment가 존재하지 않음: {name} (namespace: {namespace})"
            )
            raise DeploymentDeletionException(
                deployment_name=name,
                namespace=namespace,
                reason="Deployment does not exist",
            )

        try:
            await self.k8s_client.apps_v1.delete_namespaced_deployment(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(f"Deployment 삭제 완료: {name} (namespace: {namespace})")
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(
                    f"Deployment 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.logger.error(f"Deployment 삭제 실패: {name} - {e.reason}")
            raise DeploymentDeletionException(
                deployment_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(f"Deployment 삭제 중 예외 발생: {name} - {str(e)}")
            raise DeploymentDeletionException(
                deployment_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_deployments(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1Deployment]:
        """Deployment 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app_deployment=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1Deployment 객체 리스트

        Raises:
            DeploymentListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.apps_v1.list_namespaced_deployment(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = (
                    await self.k8s_client.apps_v1.list_deployment_for_all_namespaces(
                        label_selector=label_selector,
                        field_selector=field_selector,
                    )
                )

            return result.items

        except ApiException as e:
            self.logger.logger.error(
                f"Deployment 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise DeploymentListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(f"Deployment 목록 조회 중 예외 발생 - {str(e)}")
            raise DeploymentListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """Deployment 존재 여부 확인

        Args:
            name: Deployment 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        dep = await self.get_deployment(name, namespace)
        return dep is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1Deployment:
        """Deployment 레이블 업데이트

        Args:
            name: Deployment 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1Deployment 객체

        Raises:
            DeploymentUpdateException: 업데이트 실패 시
        """
        self.logger.info(f"Deployment 레이블 업데이트: {name} (namespace: {namespace})")

        # 존재 여부 확인
        existing = await self.get_deployment(name, namespace)
        if not existing:
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason="Deployment does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            dep = await self.k8s_client.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"Deployment 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return dep

        except ApiException as e:
            self.logger.logger.error(
                f"Deployment 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Deployment 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_replicas(
        self,
        name: str,
        namespace: str,
        replicas: int,
    ) -> V1Deployment:
        """Deployment 레플리카 수 업데이트

        Args:
            name: Deployment 이름
            namespace: 네임스페이스
            replicas: 새로운 레플리카 수

        Returns:
            업데이트된 V1Deployment 객체

        Raises:
            DeploymentUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"Deployment 레플리카 수 업데이트: {name} (namespace: {namespace}, replicas: {replicas})"
        )

        # 존재 여부 확인
        existing = await self.get_deployment(name, namespace)
        if not existing:
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason="Deployment does not exist",
            )

        # Patch 요청
        body = {"spec": {"replicas": replicas}}

        try:
            dep = await self.k8s_client.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"Deployment 레플리카 수 업데이트 완료: {name} (namespace: {namespace})"
            )
            return dep

        except ApiException as e:
            self.logger.logger.error(
                f"Deployment 레플리카 수 업데이트 실패: {name} - {e.reason}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Deployment 레플리카 수 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_container_resources(
        self,
        name: str,
        namespace: str,
        container_name: Optional[str] = None,
        requests: Optional[Dict[str, str]] = None,
        limits: Optional[Dict[str, str]] = None,
    ) -> V1Deployment:
        """Deployment 컨테이너 리소스 업데이트

        Args:
            name: Deployment 이름
            namespace: 네임스페이스
            container_name: 컨테이너 이름 (None이면 첫 번째 컨테이너)
            requests: 리소스 요청량 (예: {"cpu": "100m", "memory": "128Mi"})
            limits: 리소스 제한량 (예: {"cpu": "500m", "memory": "512Mi"})

        Returns:
            업데이트된 V1Deployment 객체

        Raises:
            DeploymentUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"Deployment 컨테이너 리소스 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_deployment(name, namespace)
        if not existing:
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason="Deployment does not exist",
            )

        # 컨테이너 찾기
        containers = existing.spec.template.spec.containers
        if not containers:
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason="No containers found in deployment",
            )

        target_container_idx = 0
        if container_name:
            for idx, container in enumerate(containers):
                if container.name == container_name:
                    target_container_idx = idx
                    break
            else:
                raise DeploymentUpdateException(
                    deployment_name=name,
                    namespace=namespace,
                    reason=f"Container '{container_name}' not found",
                )

        # 리소스 패치 구성
        resources_patch = {}
        if requests:
            resources_patch["requests"] = requests
        if limits:
            resources_patch["limits"] = limits

        if not resources_patch:
            return existing

        # Patch 요청
        body = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": containers[target_container_idx].name,
                                "resources": resources_patch,
                            }
                        ]
                    }
                }
            }
        }

        try:
            dep = await self.k8s_client.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"Deployment 컨테이너 리소스 업데이트 완료: {name} (namespace: {namespace})"
            )
            return dep

        except ApiException as e:
            self.logger.error(
                f"Deployment 컨테이너 리소스 업데이트 실패: {name} - {e.reason}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Deployment 컨테이너 리소스 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_container_images(
        self,
        name: str,
        namespace: str,
        containers: List[V1Container],
        image_pull_secrets: Optional[List[str]] = None,
    ) -> V1Deployment:
        """Deployment 컨테이너 이미지 및 imagePullSecrets 업데이트

        Args:
            name: Deployment 이름
            namespace: 네임스페이스
            containers: 이미지를 업데이트할 컨테이너 리스트
            image_pull_secrets: 이미지 풀 시크릿 이름 리스트

        Returns:
            업데이트된 V1Deployment 객체

        Raises:
            DeploymentUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"Deployment 컨테이너 이미지 업데이트: {name} (namespace: {namespace})"
        )

        pod_spec: dict = {
            "containers": [{"name": c.name, "image": c.image} for c in containers]
        }
        if image_pull_secrets is not None:
            pod_spec["imagePullSecrets"] = [{"name": s} for s in image_pull_secrets]

        body = {"spec": {"template": {"spec": pod_spec}}}

        try:
            dep = await self.k8s_client.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"Deployment 컨테이너 이미지 업데이트 완료: {name} (namespace: {namespace})"
            )
            return dep

        except ApiException as e:
            self.logger.logger.error(
                f"Deployment 컨테이너 이미지 업데이트 실패: {name} - {e.reason}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Deployment 컨테이너 이미지 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_deployment_status(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, any]]:
        """Deployment 상태 조회

        Args:
            name: Deployment 이름
            namespace: 네임스페이스

        Returns:
            Deployment 상태 정보 딕셔너리 또는 None

        Raises:
            DeploymentReadException: 조회 실패 시
        """
        deployment = await self.get_deployment(name, namespace)
        if not deployment or not deployment.status:
            return None

        status = deployment.status
        return {
            "replicas": status.replicas,
            "ready_replicas": status.ready_replicas,
            "available_replicas": status.available_replicas,
            "updated_replicas": status.updated_replicas,
            "unavailable_replicas": status.unavailable_replicas,
            "conditions": [
                {
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message,
                }
                for condition in (status.conditions or [])
            ],
        }

    async def rollout_restart(
        self,
        name: str,
        namespace: str,
    ) -> V1Deployment:
        """Deployment Rollout Restart

        kubectl rollout restart 와 동일하게,
        Pod 템플릿의 어노테이션에 restartedAt 타임스탬프를 패치하여
        롤링 업데이트를 트리거합니다.

        Args:
            name: Deployment 이름
            namespace: 네임스페이스

        Returns:
            패치된 V1Deployment 객체

        Raises:
            DeploymentUpdateException: 패치 실패 시
        """
        self.logger.info(f"Deployment Rollout Restart: {name} (namespace: {namespace})")

        existing = await self.get_deployment(name, namespace)
        if not existing:
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason="Deployment does not exist",
            )

        restarted_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": restarted_at,
                        }
                    }
                }
            }
        }

        try:
            dep = await self.k8s_client.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"Deployment Rollout Restart 완료: {name} (namespace: {namespace})"
            )
            return dep

        except ApiException as e:
            self.logger.logger.error(
                f"Deployment Rollout Restart 실패: {name} - {e.reason}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Deployment Rollout Restart 중 예외 발생: {name} - {str(e)}"
            )
            raise DeploymentUpdateException(
                deployment_name=name,
                namespace=namespace,
                reason=str(e),
            )
