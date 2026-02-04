"""Job 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1Job,
    V1ObjectMeta,
    V1JobSpec,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    JobCreationException,
    JobReadException,
    JobUpdateException,
    JobDeletionException,
    JobListException,
)


class JobManager:
    """Job 리소스를 관리하는 클래스
    """

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_job(
        self,
        name: str,
        namespace: str,
        containers: List[V1Container],
        completions: Optional[int] = None,
        parallelism: Optional[int] = None,
        backoff_limit: Optional[int] = None,
        active_deadline_seconds: Optional[int] = None,
        ttl_seconds_after_finished: Optional[int] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        pod_labels: Optional[Dict[str, str]] = None,
        pod_annotations: Optional[Dict[str, str]] = None,
        restart_policy: str = "Never",
    ) -> V1Job:
        """Job 비동기 생성

        Args:
            name: Job 이름
            namespace: 네임스페이스
            containers: 컨테이너 리스트
            completions: 성공적으로 완료해야 할 Pod 수
            parallelism: 동시에 실행할 수 있는 최대 Pod 수
            backoff_limit: 실패 재시도 횟수 (기본값: 6)
            active_deadline_seconds: Job의 최대 실행 시간 (초)
            ttl_seconds_after_finished: 완료 후 자동 삭제까지의 시간 (초)
            labels: Job 레이블
            annotations: Job 어노테이션
            pod_labels: Pod 레이블
            pod_annotations: Pod 어노테이션
            restart_policy: Pod 재시작 정책 (Never 또는 OnFailure)

        Returns:
            생성되거나 기존에 존재하는 V1Job 객체

        Raises:
            JobCreationException: Job 생성 실패 시
        """
        self.logger.info(
            f"Job 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_job(name, namespace)
        if existing:
            self.logger.info(
                f"Job 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # 기본 레이블 설정
        job_labels = labels or {"job-name": name}
        pod_template_labels = pod_labels or job_labels

        # Job 객체 생성
        job = V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=job_labels,
                annotations=annotations or {},
            ),
            spec=V1JobSpec(
                completions=completions,
                parallelism=parallelism,
                backoff_limit=backoff_limit,
                active_deadline_seconds=active_deadline_seconds,
                ttl_seconds_after_finished=ttl_seconds_after_finished,
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(
                        labels=pod_template_labels,
                        annotations=pod_annotations or {},
                    ),
                    spec=V1PodSpec(
                        containers=containers,
                        restart_policy=restart_policy,
                    ),
                ),
            ),
        )

        try:
            j = await self.k8s_client.batch_v1.create_namespaced_job(
                namespace=namespace,
                body=job,
            )
            self.logger.info(
                f"Job 생성 완료: {name} (namespace: {namespace})"
            )
            return j

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"Job 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_job(name, namespace)
                if existing:
                    return existing

            self.logger.logger.error(
                f"Job 생성 실패: {name} - {e.reason}"
            )
            raise JobCreationException(
                job_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Job 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise JobCreationException(
                job_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_job(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1Job]:
        """Job 비동기 조회

        Args:
            name: Job 이름
            namespace: 네임스페이스

        Returns:
            V1Job 객체 또는 None (존재하지 않으면)

        Raises:
            JobReadException: 조회 실패 시 (404 제외)
        """
        try:
            j = await self.k8s_client.batch_v1.read_namespaced_job(
                name=name,
                namespace=namespace,
            )
            return j

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.logger.error(
                f"Job 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise JobReadException(
                job_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Job 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise JobReadException(
                job_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_job(
        self,
        name: str,
        namespace: str,
        propagation_policy: str = "Background",
    ) -> bool:
        """Job 비동기 삭제

        Args:
            name: Job 이름
            namespace: 네임스페이스
            propagation_policy: 삭제 전파 정책 (Background, Foreground, Orphan)

        Returns:
            삭제 성공 여부

        Raises:
            JobDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"Job 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_job(name, namespace)
        if not existing:
            self.logger.warning(
                f"Job가 존재하지 않음: {name} (namespace: {namespace})"
            )
            raise JobDeletionException(
                job_name=name,
                namespace=namespace,
                reason="Job does not exist",
            )

        try:
            await self.k8s_client.batch_v1.delete_namespaced_job(
                name=name,
                namespace=namespace,
                propagation_policy=propagation_policy,
            )
            self.logger.info(
                f"Job 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.warning(
                    f"Job 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.logger.error(
                f"Job 삭제 실패: {name} - {e.reason}"
            )
            raise JobDeletionException(
                job_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Job 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise JobDeletionException(
                job_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_jobs(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1Job]:
        """Job 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app_deployment=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1Job 객체 리스트

        Raises:
            JobListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.batch_v1.list_namespaced_job(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.batch_v1.list_job_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.logger.error(
                f"Job 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise JobListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Job 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise JobListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """Job 존재 여부 확인

        Args:
            name: Job 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        j = await self.get_job(name, namespace)
        return j is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1Job:
        """Job 레이블 업데이트

        Args:
            name: Job 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1Job 객체

        Raises:
            JobUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"Job 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_job(name, namespace)
        if not existing:
            raise JobUpdateException(
                job_name=name,
                namespace=namespace,
                reason="Job does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            j = await self.k8s_client.batch_v1.patch_namespaced_job(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"Job 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return j

        except ApiException as e:
            self.logger.logger.error(
                f"Job 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise JobUpdateException(
                job_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.logger.error(
                f"Job 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise JobUpdateException(
                job_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_job_status(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, any]]:
        """Job 상태 조회

        Args:
            name: Job 이름
            namespace: 네임스페이스

        Returns:
            Job 상태 정보 딕셔너리 또는 None

        Raises:
            JobReadException: 조회 실패 시
        """
        job = await self.get_job(name, namespace)
        if not job or not job.status:
            return None

        status = job.status
        return {
            "active": status.active,
            "succeeded": status.succeeded,
            "failed": status.failed,
            "completion_time": status.completion_time,
            "start_time": status.start_time,
            "conditions": [
                {
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message,
                    "last_probe_time": condition.last_probe_time,
                    "last_transition_time": condition.last_transition_time,
                }
                for condition in (status.conditions or [])
            ],
        }

    async def is_complete(self, name: str, namespace: str) -> bool:
        """Job 완료 여부 확인

        Args:
            name: Job 이름
            namespace: 네임스페이스

        Returns:
            완료 여부
        """
        status = await self.get_job_status(name, namespace)
        if not status:
            return False

        # succeeded가 있고, active가 없으면 완료로 간주
        return status.get("succeeded", 0) > 0 and status.get("active", 0) == 0

    async def is_failed(self, name: str, namespace: str) -> bool:
        """Job 실패 여부 확인

        Args:
            name: Job 이름
            namespace: 네임스페이스

        Returns:
            실패 여부
        """
        status = await self.get_job_status(name, namespace)
        if not status:
            return False

        # conditions에서 Failed 타입을 확인
        for condition in status.get("conditions", []):
            if condition["type"] == "Failed" and condition["status"] == "True":
                return True

        return False
