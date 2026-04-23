import re
from typing import List, Dict, Any, Optional
from fastapi import Depends

from src.core.project import ProjectId
from src.api.v1.app.schemas.security_response import AppVulnerabilityResponse, VulnerabilityInfo
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository
from src.infra.harbor.manager import HarborManager


class AppSecurityVulnerabilitiesUseCase:
    """App 취약점 스캔 결과 조회 UseCase"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
        harbor_manager: HarborManager = Depends(HarborManager),
    ):
        self.app_deployment_repo = app_deployment_repo
        self.harbor_manager = harbor_manager

    async def __call__(
        self,
        app_name: str,
        project_id: str,
    ) -> List[AppVulnerabilityResponse]:
        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        responses = []
        for container in deployment.containers:
            image = container.image
            parsed = self._parse_image(image)
            if not parsed:
                continue

            report = await self.harbor_manager.get_artifact_vulnerabilities(
                project_name=parsed["project"],
                repository_name=parsed["repository"],
                reference=parsed["reference"],
            )

            # Harbor API v2.0 response parsing
            # Usually: {"application/vnd.security.vulnerability.report; version=1.1": {"vulnerabilities": [...]}}
            vulnerabilities = []
            summary = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
            
            # Find the report in the additions
            for mime_type, report_content in report.items():
                if "vulnerability.report" in mime_type:
                    vuln_list = report_content.get("vulnerabilities", [])
                    for v in vuln_list:
                        severity = v.get("severity", "Unknown")
                        summary[severity] = summary.get(severity, 0) + 1
                        
                        vulnerabilities.append(
                            VulnerabilityInfo(
                                vulnerability_id=v.get("id", ""),
                                severity=severity,
                                package=v.get("package", ""),
                                version=v.get("version", ""),
                                fix_version=v.get("fix_version"),
                                description=v.get("description"),
                            )
                        )
                    break

            responses.append(
                AppVulnerabilityResponse(
                    deployment_name=deployment.name,
                    container_name=container.name,
                    image=image,
                    vulnerabilities=vulnerabilities,
                    summary=summary,
                )
            )

        return responses

    def _parse_image(self, image: str) -> Optional[Dict[str, str]]:
        """이미지 주소 파싱 (harbor.domain/project/repo:tag)"""
        # regex to match harbor image pattern
        # domain/project/repository:tag or domain/project/repository@digest
        match = re.match(r"^([^/]+)/([^/]+)/([^:]+)(?::|@)(.+)$", image)
        if not match:
            # tag가 없는 경우 (default: latest)
            match = re.match(r"^([^/]+)/([^/]+)/([^/]+)$", image)
            if match:
                return {
                    "domain": match.group(1),
                    "project": match.group(2),
                    "repository": match.group(3),
                    "reference": "latest",
                }
            return None

        return {
            "domain": match.group(1),
            "project": match.group(2),
            "repository": match.group(3),
            "reference": match.group(4),
        }
