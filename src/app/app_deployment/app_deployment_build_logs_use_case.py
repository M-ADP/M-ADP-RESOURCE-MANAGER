from typing import List, Optional
from fastapi import Depends

from src.api.v1.app.schemas.log_response import (
    JenkinsBuildLogItem,
    JenkinsBuildLogListResponse,
    JenkinsBuildLogDetailResponse,
)
from src.dependencies.jenkins import get_jenkins_client
from src.infra.jenkins.client import JenkinsClient


class AppDeploymentBuildLogUseCase:
    """App Deployment Jenkins 빌드 로그 조회 UseCase"""

    def __init__(
        self,
        jenkins_client: JenkinsClient = Depends(get_jenkins_client),
    ):
        self.jenkins_client = jenkins_client

    async def list_builds(self, project_id: str, app_name: str) -> JenkinsBuildLogListResponse:
        """빌드 목록 조회 (app_id로 필터링)"""
        # app_id는 project_id-name 형식으로 가정
        app_id = f"{project_id}-{app_name}"
        
        all_builds = await self.jenkins_client.get_builds()
        
        filtered_builds = []
        for build in all_builds:
            # Jenkins 파라미터에서 app_id 확인
            is_match = False
            for action in build.get("actions", []):
                parameters = action.get("parameters", [])
                if not parameters:
                    continue
                
                for param in parameters:
                    if param.get("name") == "app_id" and param.get("value") == app_id:
                        is_match = True
                        break
                if is_match:
                    break
            
            if is_match:
                filtered_builds.append(
                    JenkinsBuildLogItem(
                        number=build["number"],
                        result=build.get("result"),
                        timestamp=build["timestamp"],
                        duration=build["duration"],
                        url=f"{self.jenkins_client.config.url}/job/{self.jenkins_client.config.job_name}/{build['number']}/"
                    )
                )

        return JenkinsBuildLogListResponse(
            app_id=app_id,
            builds=filtered_builds
        )

    async def get_build_log(self, build_number: int) -> JenkinsBuildLogDetailResponse:
        """단일 빌드 로그 상세 조회"""
        logs = await self.jenkins_client.get_console_text(build_number)
        return JenkinsBuildLogDetailResponse(
            number=build_number,
            logs=logs
        )
