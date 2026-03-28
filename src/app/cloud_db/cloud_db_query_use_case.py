"""Cloud DB 쿼리 실행 Use Case"""

import shlex

from fastapi import Depends
from src.core.project import ProjectId

from src.api.v1.cloud_db.schemas.request import CloudDBQueryRequest, CloudDBType
from src.api.v1.cloud_db.schemas.response import CloudDbQueryResponse
from src.app.base_use_case import BaseUseCase
from src.app.cloud_db.exceptions import CloudDbNotFoundException
from src.common.util import NameConverter
from src.dependencies.kubernetes import get_pod_manager, get_statefulset_manager
from src.infra.kubernetes.managers.pod import PodManager
from src.infra.kubernetes.managers.statefulset import StatefulSetManager


class CloudDbQueryUseCase(BaseUseCase):
    """Cloud DB Pod에 SQL 쿼리를 실행하는 Use Case"""

    def __init__(
        self,
        pod_manager: PodManager = Depends(get_pod_manager),
        sts_manager: StatefulSetManager = Depends(get_statefulset_manager),
    ):
        self.pod_manager = pod_manager
        self.sts_manager = sts_manager

    async def __call__(
        self,
        project_id: str,
        name: str,
        db_type: CloudDBType,
        payload: CloudDBQueryRequest,
    ) -> CloudDbQueryResponse:
        """StatefulSet Pod에서 SQL 쿼리 실행"""

        namespace = ProjectId(project_id).namespace
        k8s_name = NameConverter.to_k8s_name(name, prefix="db-")

        # 1. StatefulSet 존재 확인
        sts = await self.sts_manager.get_statefulset(k8s_name, namespace)
        if not sts:
            raise CloudDbNotFoundException(k8s_name, namespace)

        # 2. Running Pod 조회 (StatefulSet의 첫 번째 Pod: {name}-0)
        pod_name = f"{k8s_name}-0"

        # 3. 컨테이너 이름 결정
        container_name = payload.container_name
        if not container_name and sts.spec.template.spec.containers:
            container_name = sts.spec.template.spec.containers[0].name

        # 4. DB 타입별 실행 명령 구성
        command = self._build_command(db_type, payload.sql)

        # 5. exec 실행
        stdout, stderr = await self.pod_manager.exec_command(
            pod_name=pod_name,
            namespace=namespace,
            command=command,
        )

        return CloudDbQueryResponse(output=stdout, error=stderr)

    def _build_command(self, db_type: CloudDBType, sql: str) -> list[str]:
        """DB 타입별 실행 명령 구성 (shell을 통해 env var 확장)"""
        safe_sql = shlex.quote(sql)

        if db_type == CloudDBType.MYSQL:
            return [
                "/bin/sh", "-c",
                f'mysql -u root -p"$MYSQL_ROOT_PASSWORD" --batch --table -e {safe_sql}',
            ]
        else:  # POSTGRESQL
            return [
                "/bin/sh", "-c",
                f'PGPASSWORD="$POSTGRES_PASSWORD" psql -U postgres -t -A -c {safe_sql}',
            ]
