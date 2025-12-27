"""CronJobManager 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from kubernetes_asyncio.client import (
    V1CronJob,
    V1ObjectMeta,
    V1CronJobSpec,
    V1CronJobList,
    V1JobTemplateSpec,
    V1JobSpec,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
    V1CronJobStatus,
    V1ObjectReference,
)
from kubernetes_asyncio.client.exceptions import ApiException

from infra.kubernetes.client import KubernetesClient
from infra.kubernetes.managers.cronjob import (
    CronJobManager,
    CronJobCreationException,
    CronJobReadException,
    CronJobUpdateException,
    CronJobDeletionException,
    CronJobListException,
)


@pytest.fixture
def k8s_client():
    """KubernetesClient Mock 픽스처"""
    client = MagicMock(spec=KubernetesClient)
    client.batch_v1 = AsyncMock()
    return client


@pytest.fixture
def cronjob_manager(k8s_client):
    """CronJobManager 픽스처"""
    return CronJobManager(k8s_client)


@pytest.fixture
def mock_container():
    """Mock V1Container 객체"""
    return V1Container(
        name="test-container",
        image="busybox:latest",
        command=["echo", "Hello from CronJob"],
    )


@pytest.fixture
def mock_cronjob(mock_container):
    """Mock V1CronJob 객체"""
    return V1CronJob(
        api_version="batch/v1",
        kind="CronJob",
        metadata=V1ObjectMeta(
            name="test-cronjob",
            namespace="test-ns",
            labels={"app": "test"},
            annotations={"key": "value"},
        ),
        spec=V1CronJobSpec(
            schedule="0 */2 * * *",
            suspend=False,
            concurrency_policy="Allow",
            successful_jobs_history_limit=3,
            failed_jobs_history_limit=1,
            job_template=V1JobTemplateSpec(
                metadata=V1ObjectMeta(
                    labels={"app": "test"},
                ),
                spec=V1JobSpec(
                    template=V1PodTemplateSpec(
                        metadata=V1ObjectMeta(
                            labels={"app": "test"},
                        ),
                        spec=V1PodSpec(
                            containers=[mock_container],
                            restart_policy="OnFailure",
                        ),
                    ),
                ),
            ),
        ),
        status=V1CronJobStatus(
            active=[],
            last_schedule_time=datetime.now(),
            last_successful_time=datetime.now(),
        ),
    )


class TestCronJobManagerInit:
    """CronJobManager 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init(self, k8s_client):
        """정상 초기화 테스트"""
        manager = CronJobManager(k8s_client)
        assert manager.k8s_client == k8s_client
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_init_without_logger(self, k8s_client):
        """Logger 없이 초기화 테스트"""
        manager = CronJobManager(k8s_client)
        assert manager.logger is not None


class TestCreateCronJob:
    """CronJob 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_cronjob_success(
        self, cronjob_manager, k8s_client, mock_cronjob, mock_container
    ):
        """CronJob 생성 성공"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.batch_v1.create_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )

        result = await cronjob_manager.create_cronjob(
            name="test-cronjob",
            namespace="test-ns",
            schedule="0 */2 * * *",
            containers=[mock_container],
            labels={"app": "test"},
            annotations={"key": "value"},
        )

        assert result == mock_cronjob
        k8s_client.batch_v1.create_namespaced_cron_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_cronjob_already_exists(
        self, cronjob_manager, k8s_client, mock_cronjob, mock_container
    ):
        """이미 존재하는 CronJob 생성 (멱등성)"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )

        result = await cronjob_manager.create_cronjob(
            name="test-cronjob",
            namespace="test-ns",
            schedule="0 */2 * * *",
            containers=[mock_container],
        )

        assert result == mock_cronjob
        k8s_client.batch_v1.create_namespaced_cron_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_cronjob_conflict_409(
        self, cronjob_manager, k8s_client, mock_cronjob, mock_container
    ):
        """409 Conflict 처리 (동시 생성)"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=[
                ApiException(status=404),  # 첫 조회: 없음
                mock_cronjob,  # 재조회: 있음
            ]
        )
        k8s_client.batch_v1.create_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=409, reason="Conflict")
        )

        result = await cronjob_manager.create_cronjob(
            name="test-cronjob",
            namespace="test-ns",
            schedule="0 */2 * * *",
            containers=[mock_container],
        )

        assert result == mock_cronjob
        assert k8s_client.batch_v1.read_namespaced_cron_job.call_count == 2

    @pytest.mark.asyncio
    async def test_create_cronjob_api_exception(
        self, cronjob_manager, k8s_client, mock_container
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.batch_v1.create_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(CronJobCreationException) as exc_info:
            await cronjob_manager.create_cronjob(
                name="test-cronjob",
                namespace="test-ns",
                schedule="0 */2 * * *",
                containers=[mock_container],
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_cronjob_unexpected_exception(
        self, cronjob_manager, k8s_client, mock_container
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.batch_v1.create_namespaced_cron_job = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(CronJobCreationException) as exc_info:
            await cronjob_manager.create_cronjob(
                name="test-cronjob",
                namespace="test-ns",
                schedule="0 */2 * * *",
                containers=[mock_container],
            )

        assert "Unexpected error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_cronjob_with_custom_settings(
        self, cronjob_manager, k8s_client, mock_cronjob, mock_container
    ):
        """커스텀 설정으로 CronJob 생성"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )
        k8s_client.batch_v1.create_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )

        result = await cronjob_manager.create_cronjob(
            name="test-cronjob",
            namespace="test-ns",
            schedule="*/5 * * * *",
            containers=[mock_container],
            suspend=True,
            concurrency_policy="Forbid",
            successful_jobs_history_limit=5,
            failed_jobs_history_limit=3,
            starting_deadline_seconds=100,
            restart_policy="Never",
        )

        assert result == mock_cronjob
        k8s_client.batch_v1.create_namespaced_cron_job.assert_called_once()


class TestGetCronJob:
    """CronJob 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_cronjob_success(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """CronJob 조회 성공"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )

        result = await cronjob_manager.get_cronjob(
            name="test-cronjob",
            namespace="test-ns",
        )

        assert result == mock_cronjob

    @pytest.mark.asyncio
    async def test_get_cronjob_not_found(
        self, cronjob_manager, k8s_client
    ):
        """존재하지 않는 CronJob 조회 (404)"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await cronjob_manager.get_cronjob(
            name="test-cronjob",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cronjob_api_exception(
        self, cronjob_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(CronJobReadException) as exc_info:
            await cronjob_manager.get_cronjob(
                name="test-cronjob",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_cronjob_unexpected_exception(
        self, cronjob_manager, k8s_client
    ):
        """예상치 못한 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(CronJobReadException) as exc_info:
            await cronjob_manager.get_cronjob(
                name="test-cronjob",
                namespace="test-ns",
            )

        assert "Unexpected error" in str(exc_info.value)


class TestDeleteCronJob:
    """CronJob 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_cronjob_success(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """CronJob 삭제 성공"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.delete_namespaced_cron_job = AsyncMock()

        result = await cronjob_manager.delete_cronjob(
            name="test-cronjob",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.batch_v1.delete_namespaced_cron_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_cronjob_not_exists(
        self, cronjob_manager, k8s_client
    ):
        """존재하지 않는 CronJob 삭제 (멱등성)"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await cronjob_manager.delete_cronjob(
            name="test-cronjob",
            namespace="test-ns",
        )

        assert result is True
        k8s_client.batch_v1.delete_namespaced_cron_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_cronjob_already_deleted_404(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """삭제 중 404 발생 (이미 삭제됨)"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.delete_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await cronjob_manager.delete_cronjob(
            name="test-cronjob",
            namespace="test-ns",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_cronjob_api_exception(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.delete_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(CronJobDeletionException) as exc_info:
            await cronjob_manager.delete_cronjob(
                name="test-cronjob",
                namespace="test-ns",
            )

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_cronjob_with_grace_period(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """Grace period 지정 삭제"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.delete_namespaced_cron_job = AsyncMock()

        result = await cronjob_manager.delete_cronjob(
            name="test-cronjob",
            namespace="test-ns",
            grace_period_seconds=30,
        )

        assert result is True
        k8s_client.batch_v1.delete_namespaced_cron_job.assert_called_once_with(
            name="test-cronjob",
            namespace="test-ns",
            grace_period_seconds=30,
        )


class TestListCronJobs:
    """CronJob 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_list_cronjobs_in_namespace(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """특정 네임스페이스 내 CronJob 목록 조회"""
        mock_list = V1CronJobList(items=[mock_cronjob])
        k8s_client.batch_v1.list_namespaced_cron_job = AsyncMock(
            return_value=mock_list
        )

        result = await cronjob_manager.list_cronjobs(namespace="test-ns")

        assert len(result) == 1
        assert result[0] == mock_cronjob

    @pytest.mark.asyncio
    async def test_list_cronjobs_all_namespaces(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """전체 네임스페이스 CronJob 목록 조회"""
        mock_list = V1CronJobList(items=[mock_cronjob])
        k8s_client.batch_v1.list_cron_job_for_all_namespaces = AsyncMock(
            return_value=mock_list
        )

        result = await cronjob_manager.list_cronjobs()

        assert len(result) == 1
        assert result[0] == mock_cronjob

    @pytest.mark.asyncio
    async def test_list_cronjobs_with_selectors(
        self, cronjob_manager, k8s_client
    ):
        """셀렉터를 사용한 CronJob 목록 조회"""
        mock_list = V1CronJobList(items=[])
        k8s_client.batch_v1.list_namespaced_cron_job = AsyncMock(
            return_value=mock_list
        )

        result = await cronjob_manager.list_cronjobs(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-cronjob",
        )

        assert len(result) == 0
        k8s_client.batch_v1.list_namespaced_cron_job.assert_called_once_with(
            namespace="test-ns",
            label_selector="app=test",
            field_selector="metadata.name=test-cronjob",
        )

    @pytest.mark.asyncio
    async def test_list_cronjobs_api_exception(
        self, cronjob_manager, k8s_client
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.list_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(CronJobListException) as exc_info:
            await cronjob_manager.list_cronjobs(namespace="test-ns")

        assert "Internal Server Error" in str(exc_info.value)


class TestExists:
    """CronJob 존재 여부 확인 테스트"""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """CronJob 존재함"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )

        result = await cronjob_manager.exists(name="test-cronjob", namespace="test-ns")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, cronjob_manager, k8s_client):
        """CronJob 존재하지 않음"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await cronjob_manager.exists(name="test-cronjob", namespace="test-ns")

        assert result is False


class TestUpdateLabels:
    """CronJob 레이블 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_labels_merge(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """레이블 병합 업데이트"""
        updated_cj = V1CronJob(
            metadata=V1ObjectMeta(
                name="test-cronjob",
                namespace="test-ns",
                labels={"app": "test", "env": "prod"},
            )
        )

        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.patch_namespaced_cron_job = AsyncMock(
            return_value=updated_cj
        )

        result = await cronjob_manager.update_labels(
            name="test-cronjob",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=True,
        )

        assert result == updated_cj
        k8s_client.batch_v1.patch_namespaced_cron_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_labels_replace(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """레이블 교체 업데이트"""
        updated_cj = V1CronJob(
            metadata=V1ObjectMeta(
                name="test-cronjob",
                namespace="test-ns",
                labels={"env": "prod"},
            )
        )

        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.patch_namespaced_cron_job = AsyncMock(
            return_value=updated_cj
        )

        result = await cronjob_manager.update_labels(
            name="test-cronjob",
            namespace="test-ns",
            labels={"env": "prod"},
            merge=False,
        )

        assert result == updated_cj

    @pytest.mark.asyncio
    async def test_update_labels_not_found(self, cronjob_manager, k8s_client):
        """존재하지 않는 CronJob 레이블 업데이트"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(CronJobUpdateException) as exc_info:
            await cronjob_manager.update_labels(
                name="test-cronjob",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_labels_api_exception(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.patch_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(CronJobUpdateException) as exc_info:
            await cronjob_manager.update_labels(
                name="test-cronjob",
                namespace="test-ns",
                labels={"env": "prod"},
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestUpdateAnnotations:
    """CronJob 어노테이션 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_annotations_merge(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """어노테이션 병합 업데이트"""
        updated_cj = V1CronJob(
            metadata=V1ObjectMeta(
                name="test-cronjob",
                namespace="test-ns",
                annotations={"key": "value", "new-key": "new-value"},
            )
        )

        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.patch_namespaced_cron_job = AsyncMock(
            return_value=updated_cj
        )

        result = await cronjob_manager.update_annotations(
            name="test-cronjob",
            namespace="test-ns",
            annotations={"new-key": "new-value"},
            merge=True,
        )

        assert result == updated_cj
        k8s_client.batch_v1.patch_namespaced_cron_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_annotations_not_found(self, cronjob_manager, k8s_client):
        """존재하지 않는 CronJob 어노테이션 업데이트"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(CronJobUpdateException) as exc_info:
            await cronjob_manager.update_annotations(
                name="test-cronjob",
                namespace="test-ns",
                annotations={"new-key": "new-value"},
            )

        assert "does not exist" in str(exc_info.value)


class TestSuspendCronJob:
    """CronJob 일시 중지/재개 테스트"""

    @pytest.mark.asyncio
    async def test_suspend_cronjob_success(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """CronJob 일시 중지 성공"""
        updated_cj = V1CronJob(
            metadata=V1ObjectMeta(
                name="test-cronjob",
                namespace="test-ns",
            ),
            spec=V1CronJobSpec(
                schedule="0 */2 * * *",
                suspend=True,
                job_template=V1JobTemplateSpec(
                    spec=V1JobSpec(
                        template=V1PodTemplateSpec(
                            spec=V1PodSpec(containers=[])
                        )
                    )
                ),
            ),
        )

        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.patch_namespaced_cron_job = AsyncMock(
            return_value=updated_cj
        )

        result = await cronjob_manager.suspend_cronjob(
            name="test-cronjob",
            namespace="test-ns",
            suspend=True,
        )

        assert result == updated_cj
        k8s_client.batch_v1.patch_namespaced_cron_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_cronjob_success(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """CronJob 재개 성공"""
        updated_cj = V1CronJob(
            metadata=V1ObjectMeta(
                name="test-cronjob",
                namespace="test-ns",
            ),
            spec=V1CronJobSpec(
                schedule="0 */2 * * *",
                suspend=False,
                job_template=V1JobTemplateSpec(
                    spec=V1JobSpec(
                        template=V1PodTemplateSpec(
                            spec=V1PodSpec(containers=[])
                        )
                    )
                ),
            ),
        )

        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.patch_namespaced_cron_job = AsyncMock(
            return_value=updated_cj
        )

        result = await cronjob_manager.suspend_cronjob(
            name="test-cronjob",
            namespace="test-ns",
            suspend=False,
        )

        assert result == updated_cj

    @pytest.mark.asyncio
    async def test_suspend_cronjob_not_found(self, cronjob_manager, k8s_client):
        """존재하지 않는 CronJob 일시 중지"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(CronJobUpdateException) as exc_info:
            await cronjob_manager.suspend_cronjob(
                name="test-cronjob",
                namespace="test-ns",
            )

        assert "does not exist" in str(exc_info.value)


class TestUpdateSchedule:
    """CronJob 스케줄 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_update_schedule_success(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """스케줄 업데이트 성공"""
        updated_cj = V1CronJob(
            metadata=V1ObjectMeta(
                name="test-cronjob",
                namespace="test-ns",
            ),
            spec=V1CronJobSpec(
                schedule="*/10 * * * *",
                job_template=V1JobTemplateSpec(
                    spec=V1JobSpec(
                        template=V1PodTemplateSpec(
                            spec=V1PodSpec(containers=[])
                        )
                    )
                ),
            ),
        )

        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.patch_namespaced_cron_job = AsyncMock(
            return_value=updated_cj
        )

        result = await cronjob_manager.update_schedule(
            name="test-cronjob",
            namespace="test-ns",
            schedule="*/10 * * * *",
        )

        assert result == updated_cj
        k8s_client.batch_v1.patch_namespaced_cron_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_schedule_not_found(self, cronjob_manager, k8s_client):
        """존재하지 않는 CronJob 스케줄 업데이트"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        with pytest.raises(CronJobUpdateException) as exc_info:
            await cronjob_manager.update_schedule(
                name="test-cronjob",
                namespace="test-ns",
                schedule="*/10 * * * *",
            )

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_schedule_api_exception(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """API 예외 발생 시"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )
        k8s_client.batch_v1.patch_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=500, reason="Internal Server Error")
        )

        with pytest.raises(CronJobUpdateException) as exc_info:
            await cronjob_manager.update_schedule(
                name="test-cronjob",
                namespace="test-ns",
                schedule="*/10 * * * *",
            )

        assert "Internal Server Error" in str(exc_info.value)


class TestGetCronJobStatus:
    """CronJob 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_cronjob_status_success(
        self, cronjob_manager, k8s_client, mock_cronjob
    ):
        """CronJob 상태 조회 성공"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=mock_cronjob
        )

        result = await cronjob_manager.get_cronjob_status(
            name="test-cronjob",
            namespace="test-ns",
        )

        assert result is not None
        assert "active" in result
        assert "last_schedule_time" in result
        assert "last_successful_time" in result

    @pytest.mark.asyncio
    async def test_get_cronjob_status_not_found(
        self, cronjob_manager, k8s_client
    ):
        """존재하지 않는 CronJob 상태 조회"""
        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            side_effect=ApiException(status=404)
        )

        result = await cronjob_manager.get_cronjob_status(
            name="test-cronjob",
            namespace="test-ns",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cronjob_status_no_status(
        self, cronjob_manager, k8s_client
    ):
        """Status가 없는 CronJob"""
        cronjob_no_status = V1CronJob(
            metadata=V1ObjectMeta(
                name="test-cronjob",
                namespace="test-ns",
            ),
            spec=V1CronJobSpec(
                schedule="0 */2 * * *",
                job_template=V1JobTemplateSpec(
                    spec=V1JobSpec(
                        template=V1PodTemplateSpec(
                            spec=V1PodSpec(containers=[])
                        )
                    )
                ),
            ),
        )

        k8s_client.batch_v1.read_namespaced_cron_job = AsyncMock(
            return_value=cronjob_no_status
        )

        result = await cronjob_manager.get_cronjob_status(
            name="test-cronjob",
            namespace="test-ns",
        )

        assert result is None
