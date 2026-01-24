"""JobManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from kubernetes_asyncio.client import (
    V1Job,
    V1ObjectMeta,
    V1JobSpec,
    V1JobList,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
    V1JobStatus,
    V1JobCondition,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra.kubernetes.managers.job import (
    JobManager,
    JobCreationException,
    JobReadException,
    JobUpdateException,
    JobDeletionException,
    JobListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClientImpl Mock 픽스처"""
    client = MagicMock(spec=KubernetesClientImpl)
    client.batch_v1 = AsyncMock()
    return client


@pytest.fixture
def job_manager(k8s_client):
    """JobManager 픽스처"""
    return JobManager(k8s_client)


@pytest.fixture
def mock_container():
    """Mock V1Container 객체"""
    return V1Container(
        name="test-container",
        image="busybox:latest",
        command=["sh", "-c", "echo Hello World"],
    )


@pytest.fixture
def mock_job(mock_container):
    """Mock V1Job 객체"""
    return V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=V1ObjectMeta(
            name="test-job",
            namespace="test-ns",
            labels={"job-name": "test-job"},
            annotations={"key": "value"},
        ),
        spec=V1JobSpec(
            completions=1,
            parallelism=1,
            backoff_limit=3,
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(
                    labels={"job-name": "test-job"},
                ),
                spec=V1PodSpec(
                    containers=[mock_container],
                    restart_policy="Never",
                ),
            ),
        ),
        status=V1JobStatus(
            active=1,
            succeeded=0,
            failed=0,
            conditions=[],
        ),
    )


class TestJobManagerInit:
    """JobManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = JobManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = JobManager(k8s_client)
        assert manager.logger is not None


class TestCreateJob:
    """Job 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_job_success(
        self, job_manager, k8s_client, mock_job, mock_container
    ):
        """Job 생성 성공"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.batch_v1.create_namespaced_job = AsyncMock(
            return_value=mock_job
        )

        result = await job_manager.create_job(
            name="test-job",
            namespace="test-ns",
            containers=[mock_container],
            completions=1,
            parallelism=1,
            backoff_limit=3,
            labels={"job-name": "test-job"},
            annotations={"key": "value"},
        )

        assert result == mock_job
        k8s_client.batch_v1.create_namespaced_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_already_exists(
        self, job_manager, k8s_client, mock_job, mock_container
    ):
        """이미 존재하는 Job 생성 (멱등성)"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )

        result = await job_manager.create_job(
            name="test-job",
            namespace="test-ns",
            containers=[mock_container],
        )

        assert result == mock_job
        k8s_client.batch_v1.create_namespaced_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_job_conflict_409(
        self, job_manager, k8s_client, mock_job, mock_container
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_job,  # 재조회: 있음
            ]
        )
        k8s_client.batch_v1.create_namespaced_job = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await job_manager.create_job(
            name="test-job",
            namespace="test-ns",
            containers=[mock_container],
        )

        assert result == mock_job
        assert k8s_client.batch_v1.read_namespaced_job.call_count == 2

    @pytest.mark.asyncio
    async def test_create_job_api_exception(
        self, job_manager, k8s_client, mock_container
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.batch_v1.create_namespaced_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(JobCreationException) as exc_info:
            await job_manager.create_job(
                name="test-job",
                namespace="test-ns",
                containers=[mock_container],
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_job_unexpected_exception(
        self, job_manager, k8s_client, mock_container
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.batch_v1.create_namespaced_job = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(JobCreationException) as exc_info:
            await job_manager.create_job(
                name="test-job",
                namespace="test-ns",
                containers=[mock_container],
            )

        assert "Unexpected error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_job_with_ttl(
        self, job_manager, k8s_client, mock_job, mock_container
    ):
        """TTL 설정과 함께 Job 생성"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.batch_v1.create_namespaced_job = AsyncMock(
            return_value=mock_job
        )

        result = await job_manager.create_job(
            name="test-job",
            namespace="test-ns",
            containers=[mock_container],
            ttl_seconds_after_finished=300,
        )

        assert result == mock_job


class TestGetJob:
    """Job 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_job_success(
        self, job_manager, k8s_client, mock_job
    ):
        """Job 조회 성공"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )

        result = await job_manager.get_job(
            name="test-job",
            namespace="test-ns",
        )

        assert result == mock_job

    @pytest.mark.asyncio
    async def test_get_job_not_found(
        self, job_manager, k8s_client
    ):
        """존재하지 않는 Job 조회 (404)"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await job_manager.get_job(
            name="test-job",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_job_api_exception(
        self, job_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(JobReadException) as exc_info:
            await job_manager.get_job(
                name="test-job",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_job_unexpected_exception(
        self, job_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(JobReadException) as exc_info:
            await job_manager.get_job(
                name="test-job",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteJob:
    """Job 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_job_success(
        self, job_manager, k8s_client, mock_job
    ):
        """Job 삭제 성공"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )
        k8s_client.batch_v1.delete_namespaced_job = AsyncMock()

        result = await job_manager.delete_job(
            name="test-job",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.batch_v1.delete_namespaced_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_job_not_exists(
        self, job_manager, k8s_client
    ):
        """존재하지 않는 Job 삭제"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(JobDeletionException) as exc_info:
            await job_manager.delete_job(
                name="test-job",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_job_already_deleted_404(
        self, job_manager, k8s_client, mock_job
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )
        k8s_client.batch_v1.delete_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await job_manager.delete_job(
            name="test-job",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_job_api_exception(
        self, job_manager, k8s_client, mock_job
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )
        k8s_client.batch_v1.delete_namespaced_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(JobDeletionException) as exc_info:
            await job_manager.delete_job(
                name="test-job",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_job_with_propagation_policy(
        self, job_manager, k8s_client, mock_job
    ):
        """Propagation policy 지정 삭제"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )
        k8s_client.batch_v1.delete_namespaced_job = AsyncMock()

        result = await job_manager.delete_job(
            name="test-job",
            namespace="test-ns",
            propagation_policy="Foreground",
        )

        assert result is True
        k8s_client.batch_v1.delete_namespaced_job.assert_called_once_with(
            name="test-job",
            namespace="test-ns",
            propagation_policy="Foreground",
        )


class TestListJobs:
    """Job 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_jobs_in_namespace(
        self, job_manager, k8s_client, mock_job
    ):
        """특정 네임스페이스 내 Job 목록 조회"""
        mock_list = V1JobList(items=[mock_job])
        k8s_client.batch_v1.list_namespaced_job = AsyncMock(
            return_value=mock_list
        )

        result = await job_manager.list_jobs(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_job

    @pytest.mark.asyncio
    async def test_list_jobs_all_namespaces(
        self, job_manager, k8s_client, mock_job
    ):
        """전체 네임스페이스 Job 목록 조회"""
        mock_list = V1JobList(items=[mock_job])
        k8s_client.batch_v1.list_job_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await job_manager.list_jobs()

        assert len(result) == 1
        assert result[0] == mock_job

    @pytest.mark.asyncio
    async def test_list_jobs_with_selectors(
        self, job_manager, k8s_client
    ):
        """셀렉터를 사용한 Job 목록 조회"""
        mock_list = V1JobList(items=[])
        k8s_client.batch_v1.list_namespaced_job = AsyncMock(
            return_value=mock_list
        )

        result = await job_manager.list_jobs(
            namespace="test-ns",
            label_selector="job-name=test-job",
            field_selector="metadata.name=test-job",
        )

        assert len(result) == 0
        k8s_client.batch_v1.list_namespaced_job.assert_called_once_with(
            namespace="test-ns",
            label_selector="job-name=test-job",
            field_selector="metadata.name=test-job",
        )

    @pytest.mark.asyncio
    async def test_list_jobs_api_exception(
        self, job_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.list_namespaced_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(JobListException) as exc_info:
            await job_manager.list_jobs(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """Job 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, job_manager, k8s_client, mock_job
    ):
        """Job 존재함"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )

        result = await job_manager.exists(name="test-job", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, job_manager, k8s_client):
        """Job 존재하지 않음"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await job_manager.exists(name="test-job", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """Job 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, job_manager, k8s_client, mock_job
    ):
        """레이블 병합 업데이트"""
        updated_job = V1Job(
            metadata=V1ObjectMeta(
                name="test-job",
                namespace="test-ns",
                labels={"job-name": "test-job", "env": "prod"},
            )
        )

        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )
        k8s_client.batch_v1.patch_namespaced_job = AsyncMock(
            return_value=updated_job
        )

        result = await job_manager.update_labels(
            name="test-job",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_job
        k8s_client.batch_v1.patch_namespaced_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, job_manager, k8s_client, mock_job
    ):
        """레이블 교체 업데이트"""
        updated_job = V1Job(
            metadata=V1ObjectMeta(
                name="test-job",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )
        k8s_client.batch_v1.patch_namespaced_job = AsyncMock(
            return_value=updated_job
        )

        result = await job_manager.update_labels(
            name="test-job",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_job

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, job_manager, k8s_client):
        """존재하지 않는 Job 레이블 업데이트"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(JobUpdateException) as exc_info:
            await job_manager.update_labels(
                name="test-job",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, job_manager, k8s_client, mock_job
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )
        k8s_client.batch_v1.patch_namespaced_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(JobUpdateException) as exc_info:
            await job_manager.update_labels(
                name="test-job",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestGetJobStatus:
    """Job 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_job_status_success(
        self, job_manager, k8s_client, mock_job
    ):
        """Job 상태 조회 성공"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=mock_job
        )

        result = await job_manager.get_job_status(
            name="test-job",
            namespace="test-ns",
        )

        assert result is not None
        assert result["active"] == 1
        assert result["succeeded"] == 0
        assert result["failed"] == 0
        assert len(result["conditions"]) == 0

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(
        self, job_manager, k8s_client
    ):
        """존재하지 않는 Job 상태 조회"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await job_manager.get_job_status(
            name="test-job",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_job_status_no_status(
        self, job_manager, k8s_client
    ):
        """Status가 없는 Job"""
        job_no_status = V1Job(
            metadata=V1ObjectMeta(
                name="test-job",
                namespace="test-ns",
            ),
            spec=V1JobSpec(
                template=V1PodTemplateSpec(
                    spec=V1PodSpec(containers=[])
                )
            ),
        )

        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=job_no_status
        )

        result = await job_manager.get_job_status(
            name="test-job",
            namespace="test-ns",
        )

        assert result is None


class TestIsComplete:
    """Job 완료 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_is_complete_true(
        self, job_manager, k8s_client
    ):
        """Job 완료됨"""
        completed_job = V1Job(
            metadata=V1ObjectMeta(name="test-job", namespace="test-ns"),
            spec=V1JobSpec(template=V1PodTemplateSpec(spec=V1PodSpec(containers=[]))),
            status=V1JobStatus(active=0, succeeded=1, failed=0),
        )
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=completed_job
        )

        result = await job_manager.is_complete(name="test-job", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_complete_false_active(
        self, job_manager, k8s_client
    ):
        """Job 아직 실행 중"""
        running_job = V1Job(
            metadata=V1ObjectMeta(name="test-job", namespace="test-ns"),
            spec=V1JobSpec(template=V1PodTemplateSpec(spec=V1PodSpec(containers=[]))),
            status=V1JobStatus(active=1, succeeded=0, failed=0),
        )
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=running_job
        )

        result = await job_manager.is_complete(name="test-job", namespace="test-ns")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_complete_false_not_found(
        self, job_manager, k8s_client
    ):
        """Job 존재하지 않음"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await job_manager.is_complete(name="test-job", namespace="test-ns")

        assert result is False


class TestIsFailed:
    """Job 실패 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_is_failed_true(
        self, job_manager, k8s_client
    ):
        """Job 실패함"""
        failed_job = V1Job(
            metadata=V1ObjectMeta(name="test-job", namespace="test-ns"),
            spec=V1JobSpec(template=V1PodTemplateSpec(spec=V1PodSpec(containers=[]))),
            status=V1JobStatus(
                active=0,
                succeeded=0,
                failed=1,
                conditions=[
                    V1JobCondition(
                        type="Failed",
                        status="True",
                        reason="BackoffLimitExceeded",
                        message="Job has reached the specified backoff limit",
                    )
                ],
            ),
        )
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=failed_job
        )

        result = await job_manager.is_failed(name="test-job", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_failed_false(
        self, job_manager, k8s_client
    ):
        """Job 실패하지 않음"""
        running_job = V1Job(
            metadata=V1ObjectMeta(name="test-job", namespace="test-ns"),
            spec=V1JobSpec(template=V1PodTemplateSpec(spec=V1PodSpec(containers=[]))),
            status=V1JobStatus(active=1, succeeded=0, failed=0, conditions=[]),
        )
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            return_value=running_job
        )

        result = await job_manager.is_failed(name="test-job", namespace="test-ns")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_failed_not_found(
        self, job_manager, k8s_client
    ):
        """Job 존재하지 않음"""
        k8s_client.batch_v1.read_namespaced_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await job_manager.is_failed(name="test-job", namespace="test-ns")

        assert result is False
