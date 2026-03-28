"""CronJob 리소스 관리 클래스"""

import datetime
from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1CronJob,
    V1Job,
    V1ObjectMeta,
    V1CronJobSpec,
    V1JobTemplateSpec,
    V1JobSpec,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    CronJobCreationException,
    CronJobReadException,
    CronJobUpdateException,
    CronJobDeletionException,
    CronJobListException,
)


class CronJobManager:
    """CronJob 리소스를 관리하는 클래스"""

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_cronjob(
        self,
        name: str,
        namespace: str,
        schedule: str,
        containers: List[V1Container],
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        suspend: bool = False,
        concurrency_policy: str = "Allow",
        successful_jobs_history_limit: Optional[int] = 3,
        failed_jobs_history_limit: Optional[int] = 1,
        starting_deadline_seconds: Optional[int] = None,
        restart_policy: str = "OnFailure",
    ) -> V1CronJob:
        """CronJob 비동기 생성

        Args:
            name: CronJob 이름
            namespace: 네임스페이스
            schedule: Cron 스케줄 표현식 (예: "0 */2 * * *")
            containers: 컨테이너 리스트
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리
            suspend: CronJob 일시 중지 여부
            concurrency_policy: 동시성 정책 (Allow, Forbid, Replace)
            successful_jobs_history_limit: 성공한 Job 보관 개수
            failed_jobs_history_limit: 실패한 Job 보관 개수
            starting_deadline_seconds: Job 시작 데드라인 (초)
            restart_policy: Pod 재시작 정책 (OnFailure, Never)

        Returns:
            생성되거나 기존에 존재하는 V1CronJob 객체

        Raises:
            CronJobCreationException: CronJob 생성 실패 시
        """
        self.logger.info(
            f"CronJob 생성 시도: {name} (namespace: {namespace}, schedule: {schedule})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_cronjob(name, namespace)
        if existing:
            self.logger.info(f"CronJob 이미 존재함: {name} (namespace: {namespace})")
            return existing

        # 기본 레이블 설정
        cronjob_labels = labels or {"app_deployment": name}

        # CronJob 객체 생성
        cronjob = V1CronJob(
            api_version="batch/v1",
            kind="CronJob",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=cronjob_labels,
                annotations=annotations or {},
            ),
            spec=V1CronJobSpec(
                schedule=schedule,
                suspend=suspend,
                concurrency_policy=concurrency_policy,
                successful_jobs_history_limit=successful_jobs_history_limit,
                failed_jobs_history_limit=failed_jobs_history_limit,
                starting_deadline_seconds=starting_deadline_seconds,
                job_template=V1JobTemplateSpec(
                    metadata=V1ObjectMeta(
                        labels=cronjob_labels,
                    ),
                    spec=V1JobSpec(
                        template=V1PodTemplateSpec(
                            metadata=V1ObjectMeta(
                                labels=cronjob_labels,
                            ),
                            spec=V1PodSpec(
                                containers=containers,
                                restart_policy=restart_policy,
                            ),
                        ),
                    ),
                ),
            ),
        )

        try:
            cj = await self.k8s_client.batch_v1.create_namespaced_cron_job(
                namespace=namespace,
                body=cronjob,
            )
            self.logger.info(f"CronJob 생성 완료: {name} (namespace: {namespace})")
            return cj

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(f"CronJob 생성 충돌 (409), 재조회: {name}")
                existing = await self.get_cronjob(name, namespace)
                if existing:
                    return existing

            self.logger.error(f"CronJob 생성 실패: {name} - {e.reason}")
            raise CronJobCreationException(
                cronjob_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"CronJob 생성 중 예외 발생: {name} - {str(e)}")
            raise CronJobCreationException(
                cronjob_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_cronjob(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1CronJob]:
        """CronJob 비동기 조회

        Args:
            name: CronJob 이름
            namespace: 네임스페이스

        Returns:
            V1CronJob 객체 또는 None (존재하지 않으면)

        Raises:
            CronJobReadException: 조회 실패 시 (404 제외)
        """
        try:
            cj = await self.k8s_client.batch_v1.read_namespaced_cron_job(
                name=name,
                namespace=namespace,
            )
            return cj

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.error(
                f"CronJob 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise CronJobReadException(
                cronjob_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"CronJob 조회 중 예외 발생: {name} - {str(e)}")
            raise CronJobReadException(
                cronjob_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_cronjob(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """CronJob 비동기 삭제

        Args:
            name: CronJob 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            CronJobDeletionException: 삭제 실패 시
        """
        self.logger.info(f"CronJob 삭제 시도: {name} (namespace: {namespace})")

        # 존재 여부 확인
        existing = await self.get_cronjob(name, namespace)
        if not existing:
            self.logger.info(
                f"CronJob가 존재하지 않음: {name} (namespace: {namespace})"
            )
            return True

        try:
            await self.k8s_client.batch_v1.delete_namespaced_cron_job(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(f"CronJob 삭제 완료: {name} (namespace: {namespace})")
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.info(
                    f"CronJob 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.error(f"CronJob 삭제 실패: {name} - {e.reason}")
            raise CronJobDeletionException(
                cronjob_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"CronJob 삭제 중 예외 발생: {name} - {str(e)}")
            raise CronJobDeletionException(
                cronjob_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_cronjobs(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1CronJob]:
        """CronJob 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app_deployment=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1CronJob 객체 리스트

        Raises:
            CronJobListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.batch_v1.list_namespaced_cron_job(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = (
                    await self.k8s_client.batch_v1.list_cron_job_for_all_namespaces(
                        label_selector=label_selector,
                        field_selector=field_selector,
                    )
                )

            return result.items

        except ApiException as e:
            self.logger.error(
                f"CronJob 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise CronJobListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"CronJob 목록 조회 중 예외 발생 - {str(e)}")
            raise CronJobListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """CronJob 존재 여부 확인

        Args:
            name: CronJob 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        cj = await self.get_cronjob(name, namespace)
        return cj is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1CronJob:
        """CronJob 레이블 업데이트

        Args:
            name: CronJob 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1CronJob 객체

        Raises:
            CronJobUpdateException: 업데이트 실패 시
        """
        self.logger.info(f"CronJob 레이블 업데이트: {name} (namespace: {namespace})")

        # 존재 여부 확인
        existing = await self.get_cronjob(name, namespace)
        if not existing:
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason="CronJob does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            cj = await self.k8s_client.batch_v1.patch_namespaced_cron_job(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"CronJob 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return cj

        except ApiException as e:
            self.logger.error(f"CronJob 레이블 업데이트 실패: {name} - {e.reason}")
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"CronJob 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_annotations(
        self,
        name: str,
        namespace: str,
        annotations: Dict[str, str],
        merge: bool = True,
    ) -> V1CronJob:
        """CronJob 어노테이션 업데이트

        Args:
            name: CronJob 이름
            namespace: 네임스페이스
            annotations: 새로운 어노테이션 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1CronJob 객체

        Raises:
            CronJobUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"CronJob 어노테이션 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_cronjob(name, namespace)
        if not existing:
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason="CronJob does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.annotations:
            new_annotations = {**existing.metadata.annotations, **annotations}
        else:
            new_annotations = annotations

        # Patch 요청
        body = {"metadata": {"annotations": new_annotations}}

        try:
            cj = await self.k8s_client.batch_v1.patch_namespaced_cron_job(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"CronJob 어노테이션 업데이트 완료: {name} (namespace: {namespace})"
            )
            return cj

        except ApiException as e:
            self.logger.error(f"CronJob 어노테이션 업데이트 실패: {name} - {e.reason}")
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"CronJob 어노테이션 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def suspend_cronjob(
        self,
        name: str,
        namespace: str,
        suspend: bool = True,
    ) -> V1CronJob:
        """CronJob 일시 중지/재개

        Args:
            name: CronJob 이름
            namespace: 네임스페이스
            suspend: True면 중지, False면 재개

        Returns:
            업데이트된 V1CronJob 객체

        Raises:
            CronJobUpdateException: 업데이트 실패 시
        """
        action = "일시 중지" if suspend else "재개"
        self.logger.info(f"CronJob {action}: {name} (namespace: {namespace})")

        # 존재 여부 확인
        existing = await self.get_cronjob(name, namespace)
        if not existing:
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason="CronJob does not exist",
            )

        # Patch 요청
        body = {"spec": {"suspend": suspend}}

        try:
            cj = await self.k8s_client.batch_v1.patch_namespaced_cron_job(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(f"CronJob {action} 완료: {name} (namespace: {namespace})")
            return cj

        except ApiException as e:
            self.logger.error(f"CronJob {action} 실패: {name} - {e.reason}")
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"CronJob {action} 중 예외 발생: {name} - {str(e)}")
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_schedule(
        self,
        name: str,
        namespace: str,
        schedule: str,
    ) -> V1CronJob:
        """CronJob 스케줄 업데이트

        Args:
            name: CronJob 이름
            namespace: 네임스페이스
            schedule: 새로운 Cron 스케줄 표현식

        Returns:
            업데이트된 V1CronJob 객체

        Raises:
            CronJobUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"CronJob 스케줄 업데이트: {name} (namespace: {namespace}, schedule: {schedule})"
        )

        # 존재 여부 확인
        existing = await self.get_cronjob(name, namespace)
        if not existing:
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason="CronJob does not exist",
            )

        # Patch 요청
        body = {"spec": {"schedule": schedule}}

        try:
            cj = await self.k8s_client.batch_v1.patch_namespaced_cron_job(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"CronJob 스케줄 업데이트 완료: {name} (namespace: {namespace})"
            )
            return cj

        except ApiException as e:
            self.logger.error(f"CronJob 스케줄 업데이트 실패: {name} - {e.reason}")
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"CronJob 스케줄 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise CronJobUpdateException(
                cronjob_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_cronjob_status(
        self,
        name: str,
        namespace: str,
    ) -> Optional[Dict[str, any]]:
        """CronJob 상태 조회

        Args:
            name: CronJob 이름
            namespace: 네임스페이스

        Returns:
            CronJob 상태 정보 딕셔너리 또는 None

        Raises:
            CronJobReadException: 조회 실패 시
        """
        cronjob = await self.get_cronjob(name, namespace)
        if not cronjob or not cronjob.status:
            return None

        status = cronjob.status
        return {
            "active": [job.name for job in (status.active or [])],
            "last_schedule_time": status.last_schedule_time,
            "last_successful_time": status.last_successful_time,
        }

    async def trigger_cronjob(
        self,
        name: str,
        namespace: str,
    ) -> V1Job:
        """CronJob 즉시 실행 — jobTemplate으로 Job을 직접 생성

        CronJob의 spec.jobTemplate을 복사하여 일회성 Job을 즉시 생성합니다.
        배치 적체 해소, 수동 재실행 등에 사용합니다.

        Args:
            name: CronJob 이름
            namespace: 네임스페이스

        Returns:
            생성된 V1Job 객체

        Raises:
            CronJobReadException: CronJob 조회 실패 시
            CronJobCreationException: Job 생성 실패 시
        """
        self.logger.info(f"CronJob 즉시 실행 요청: {name} (namespace: {namespace})")

        cj = await self.get_cronjob(name, namespace)
        if cj is None:
            raise CronJobReadException(
                cronjob_name=name,
                namespace=namespace,
                reason="CronJob does not exist",
            )

        # 고유한 Job 이름 생성 (CronJob 이름 + 타임스탬프)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        job_name = f"{name}-manual-{timestamp}"

        # jobTemplate에서 spec 복사 후 ttl 주입 (완료 즉시 자동 삭제)
        job_template_spec = (
            cj.spec.job_template.spec if cj.spec and cj.spec.job_template else None
        )
        if job_template_spec is not None:
            job_template_spec.ttl_seconds_after_finished = 0

        job = V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=V1ObjectMeta(
                name=job_name,
                namespace=namespace,
                labels={
                    **(
                        cj.spec.job_template.metadata.labels
                        if cj.spec
                        and cj.spec.job_template
                        and cj.spec.job_template.metadata
                        and cj.spec.job_template.metadata.labels
                        else {}
                    ),
                    "cronjob-name": name,
                    "triggered-manually": "true",
                },
                annotations={
                    "cronjob-name": name,
                    "triggered-at": datetime.datetime.utcnow().isoformat() + "Z",
                },
            ),
            spec=job_template_spec,
        )

        try:
            created_job = await self.k8s_client.batch_v1.create_namespaced_job(
                namespace=namespace,
                body=job,
            )
            self.logger.info(
                f"CronJob 즉시 실행 Job 생성 완료: {job_name} (namespace: {namespace})"
            )
            return created_job

        except ApiException as e:
            self.logger.error(f"CronJob 즉시 실행 Job 생성 실패: {name} - {e.reason}")
            raise CronJobCreationException(
                cronjob_name=name,
                namespace=namespace,
                reason=e.reason or str(e),
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(f"CronJob 즉시 실행 중 예외 발생: {name} - {str(e)}")
            raise CronJobCreationException(
                cronjob_name=name,
                namespace=namespace,
                reason=str(e),
            )
