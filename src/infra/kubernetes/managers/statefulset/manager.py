"""StatefulSet 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1StatefulSet,
    V1ObjectMeta,
    V1StatefulSetSpec,
    V1LabelSelector,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
    V1StatefulSetUpdateStrategy,
    V1PersistentVolumeClaim,
    V1LocalObjectReference,
    V1Volume,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    StatefulSetCreationException,
    StatefulSetReadException,
    StatefulSetUpdateException,
    StatefulSetDeletionException,
    StatefulSetListException,
)


class StatefulSetManager:
    """StatefulSet 리소스를 관리하는 클래스"""

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_statefulset(
        self,
        name: str,
        namespace: str,
        service_name: str,
        replicas: int,
        selector: Dict[str, str],
        containers: List[V1Container],
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        volume_claim_templates: Optional[List[V1PersistentVolumeClaim]] = None,
        volumes: Optional[List[V1Volume]] = None,
        service_account_name: Optional[str] = None,
        image_pull_secrets: Optional[List[str]] = None,
        update_strategy: Optional[str] = "RollingUpdate",
        pod_management_policy: Optional[str] = "OrderedReady",
    ) -> V1StatefulSet:
        """StatefulSet 비동기 생성

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스
            service_name: Headless Service 이름
            replicas: Pod 개수
            selector: Pod 선택 레이블 (예: {"app_deployment": "myapp"})
            containers: 컨테이너 리스트
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리
            volume_claim_templates: PVC 템플릿 리스트
            update_strategy: 업데이트 전략 (RollingUpdate, OnDelete)
            pod_management_policy: Pod 관리 정책 (OrderedReady, Parallel)

        Returns:
            생성되거나 기존에 존재하는 V1StatefulSet 객체

        Raises:
            StatefulSetCreationException: StatefulSet 생성 실패 시
        """
        self.logger.info(
            f"StatefulSet 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_statefulset(name, namespace)
        if existing:
            self.logger.info(
                f"StatefulSet 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # StatefulSet 객체 생성
        statefulset = V1StatefulSet(
            api_version="apps/v1",
            kind="StatefulSet",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {},
                annotations=annotations or {},
            ),
            spec=V1StatefulSetSpec(
                service_name=service_name,
                replicas=replicas,
                selector=V1LabelSelector(match_labels=selector),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(
                        labels=selector,
                    ),
                    spec=V1PodSpec(
                        containers=containers,
                        volumes=volumes,
                        service_account_name=service_account_name,
                        image_pull_secrets=[V1LocalObjectReference(name=s) for s in image_pull_secrets] if image_pull_secrets else None,
                    ),
                ),
                volume_claim_templates=volume_claim_templates,
                update_strategy=V1StatefulSetUpdateStrategy(
                    type=update_strategy,
                ),
                pod_management_policy=pod_management_policy,
            ),
        )

        try:
            sts = await self.k8s_client.apps_v1.create_namespaced_stateful_set(
                namespace=namespace,
                body=statefulset,
            )
            self.logger.info(
                f"StatefulSet 생성 완료: {name} (namespace: {namespace})"
            )
            return sts

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"StatefulSet 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_statefulset(name, namespace)
                if existing:
                    return existing

            self.logger.error(
                f"StatefulSet 생성 실패: {name} - {e.reason}"
            )
            raise StatefulSetCreationException(
                statefulset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"StatefulSet 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise StatefulSetCreationException(
                statefulset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_statefulset(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1StatefulSet]:
        """StatefulSet 비동기 조회

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스

        Returns:
            V1StatefulSet 객체 또는 None (존재하지 않으면)

        Raises:
            StatefulSetReadException: 조회 실패 시 (404 제외)
        """
        try:
            sts = await self.k8s_client.apps_v1.read_namespaced_stateful_set(
                name=name,
                namespace=namespace,
            )
            return sts

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.error(
                f"StatefulSet 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise StatefulSetReadException(
                statefulset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"StatefulSet 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise StatefulSetReadException(
                statefulset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_statefulset(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """StatefulSet 비동기 삭제

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            StatefulSetDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"StatefulSet 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_statefulset(name, namespace)
        if not existing:
            self.logger.info(
                f"StatefulSet가 존재하지 않음: {name} (namespace: {namespace})"
            )
            return True

        try:
            await self.k8s_client.apps_v1.delete_namespaced_stateful_set(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(
                f"StatefulSet 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.info(
                    f"StatefulSet 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.error(
                f"StatefulSet 삭제 실패: {name} - {e.reason}"
            )
            raise StatefulSetDeletionException(
                statefulset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"StatefulSet 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise StatefulSetDeletionException(
                statefulset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_statefulsets(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1StatefulSet]:
        """StatefulSet 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app_deployment=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1StatefulSet 객체 리스트

        Raises:
            StatefulSetListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.apps_v1.list_namespaced_stateful_set(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.apps_v1.list_stateful_set_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.error(
                f"StatefulSet 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise StatefulSetListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"StatefulSet 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise StatefulSetListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """StatefulSet 존재 여부 확인

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        sts = await self.get_statefulset(name, namespace)
        return sts is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1StatefulSet:
        """StatefulSet 레이블 업데이트

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1StatefulSet 객체

        Raises:
            StatefulSetUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"StatefulSet 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_statefulset(name, namespace)
        if not existing:
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason="StatefulSet does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            sts = await self.k8s_client.apps_v1.patch_namespaced_stateful_set(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"StatefulSet 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return sts

        except ApiException as e:
            self.logger.error(
                f"StatefulSet 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"StatefulSet 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_annotations(
        self,
        name: str,
        namespace: str,
        annotations: Dict[str, str],
        merge: bool = True,
    ) -> V1StatefulSet:
        """StatefulSet 어노테이션 업데이트

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스
            annotations: 새로운 어노테이션 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1StatefulSet 객체

        Raises:
            StatefulSetUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"StatefulSet 어노테이션 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_statefulset(name, namespace)
        if not existing:
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason="StatefulSet does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.annotations:
            new_annotations = {**existing.metadata.annotations, **annotations}
        else:
            new_annotations = annotations

        # Patch 요청
        body = {"metadata": {"annotations": new_annotations}}

        try:
            sts = await self.k8s_client.apps_v1.patch_namespaced_stateful_set(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"StatefulSet 어노테이션 업데이트 완료: {name} (namespace: {namespace})"
            )
            return sts

        except ApiException as e:
            self.logger.error(
                f"StatefulSet 어노테이션 업데이트 실패: {name} - {e.reason}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"StatefulSet 어노테이션 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def scale_statefulset(
        self,
        name: str,
        namespace: str,
        replicas: int,
    ) -> V1StatefulSet:
        """StatefulSet 스케일 조정

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스
            replicas: 새로운 replica 개수

        Returns:
            업데이트된 V1StatefulSet 객체

        Raises:
            StatefulSetUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"StatefulSet 스케일 조정: {name} → {replicas} replicas (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_statefulset(name, namespace)
        if not existing:
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason="StatefulSet does not exist",
            )

        # Patch 요청
        body = {"spec": {"replicas": replicas}}

        try:
            sts = await self.k8s_client.apps_v1.patch_namespaced_stateful_set(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"StatefulSet 스케일 조정 완료: {name} → {replicas} replicas"
            )
            return sts

        except ApiException as e:
            self.logger.error(
                f"StatefulSet 스케일 조정 실패: {name} - {e.reason}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"StatefulSet 스케일 조정 중 예외 발생: {name} - {str(e)}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_statefulset_status(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, any]]:
        """StatefulSet 상태 조회

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스

        Returns:
            StatefulSet 상태 정보 또는 None
        """
        sts = await self.get_statefulset(name, namespace)
        if not sts or not sts.status:
            return None

        return {
            "replicas": sts.status.replicas,
            "ready_replicas": sts.status.ready_replicas,
            "current_replicas": sts.status.current_replicas,
            "updated_replicas": sts.status.updated_replicas,
            "current_revision": sts.status.current_revision,
            "update_revision": sts.status.update_revision,
        }

    async def update_container_images(
        self,
        name: str,
        namespace: str,
        containers: List[V1Container],
        image_pull_secrets: Optional[List[str]] = None,
    ) -> V1StatefulSet:
        """StatefulSet 컨테이너 이미지 업데이트

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스
            containers: 컨테이너 리스트 (name, image)
            image_pull_secrets: 이미지 풀 시크릿 목록

        Returns:
            업데이트된 V1StatefulSet 객체

        Raises:
            StatefulSetUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"StatefulSet 컨테이너 이미지 업데이트: {name} (namespace: {namespace})"
        )

        patch_containers = [{"name": c.name, "image": c.image} for c in containers]
        body: dict = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": patch_containers,
                    }
                }
            }
        }
        if image_pull_secrets is not None:
            body["spec"]["template"]["spec"]["imagePullSecrets"] = [
                {"name": s} for s in image_pull_secrets
            ]

        try:
            sts = await self.k8s_client.apps_v1.patch_namespaced_stateful_set(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"StatefulSet 컨테이너 이미지 업데이트 완료: {name} (namespace: {namespace})"
            )
            return sts

        except ApiException as e:
            self.logger.error(
                f"StatefulSet 컨테이너 이미지 업데이트 실패: {name} - {e.reason}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"StatefulSet 컨테이너 이미지 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_container_resources(
        self,
        name: str,
        namespace: str,
        container_name: str,
        requests: Optional[Dict[str, str]] = None,
        limits: Optional[Dict[str, str]] = None,
    ) -> V1StatefulSet:
        """StatefulSet 컨테이너 리소스 업데이트

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스
            container_name: 수정할 컨테이너 이름
            requests: 새로운 리소스 요청량 (예: {"cpu": "200m", "memory": "256Mi"})
            limits: 새로운 리소스 제한량 (예: {"cpu": "500m", "memory": "512Mi"})

        Returns:
            업데이트된 V1StatefulSet 객체

        Raises:
            StatefulSetUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"StatefulSet 컨테이너 리소스 업데이트: {name}/{container_name} (namespace: {namespace})"
        )

        existing = await self.get_statefulset(name, namespace)
        if not existing or not existing.spec or not existing.spec.template or not existing.spec.template.spec:
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason="StatefulSet does not exist or spec is missing",
            )

        patch_containers = []
        for c in existing.spec.template.spec.containers or []:
            if c.name == container_name:
                current_res = {}
                if c.resources:
                    if c.resources.requests:
                        current_res["requests"] = dict(c.resources.requests)
                    if c.resources.limits:
                        current_res["limits"] = dict(c.resources.limits)
                if requests is not None:
                    current_res["requests"] = {**(current_res.get("requests") or {}), **requests}
                if limits is not None:
                    current_res["limits"] = {**(current_res.get("limits") or {}), **limits}
                patch_containers.append({"name": c.name, "image": c.image, "resources": current_res})
            else:
                patch_containers.append({"name": c.name, "image": c.image})

        body = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": patch_containers,
                    }
                }
            }
        }

        try:
            sts = await self.k8s_client.apps_v1.patch_namespaced_stateful_set(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"StatefulSet 컨테이너 리소스 업데이트 완료: {name}/{container_name}"
            )
            return sts

        except ApiException as e:
            self.logger.error(
                f"StatefulSet 컨테이너 리소스 업데이트 실패: {name} - {e.reason}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"StatefulSet 컨테이너 리소스 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise StatefulSetUpdateException(
                statefulset_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def is_ready(
        self,
        name: str,
        namespace: str,
    ) -> bool:
        """StatefulSet이 준비 상태인지 확인

        Args:
            name: StatefulSet 이름
            namespace: 네임스페이스

        Returns:
            준비 상태 여부
        """
        sts = await self.get_statefulset(name, namespace)
        if not sts or not sts.status or not sts.spec:
            return False

        # replicas와 ready_replicas가 같으면 준비 완료
        return (
            sts.status.ready_replicas is not None
            and sts.spec.replicas is not None
            and sts.status.ready_replicas == sts.spec.replicas
        )
