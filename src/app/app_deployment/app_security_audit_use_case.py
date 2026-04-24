from fastapi import Depends

from src.core.project import ProjectId
from src.api.v1.app.schemas.security_response import AppSecurityAuditResponse, AuditFinding
from src.app.app_deployment.exceptions import DeploymentNotFoundException
from src.common.util import NameConverter
from src.core.app_deployment import AppDeploymentRepository
from src.dependencies.kubernetes import get_app_deployment_repository

_DANGEROUS_CAPS = {"NET_ADMIN", "SYS_ADMIN", "SYS_PTRACE", "SYS_MODULE", "ALL"}


class AppSecurityAuditUseCase:
    """App 보안 감사 UseCase (읽기 전용)"""

    def __init__(
        self,
        app_deployment_repo: AppDeploymentRepository = Depends(get_app_deployment_repository),
    ):
        self.app_deployment_repo = app_deployment_repo

    async def __call__(
        self,
        app_name: str,
        project_id: str,
    ) -> AppSecurityAuditResponse:
        namespace = ProjectId(project_id).namespace
        app_name = NameConverter.to_k8s_name(app_name)

        deployment = await self.app_deployment_repo.find_deployment(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(name=app_name, namespace=namespace)

        findings = []
        for container in deployment.containers:
            sc = container.security_context

            if sc and sc.privileged:
                findings.append(AuditFinding(
                    container_name=container.name,
                    severity="CRITICAL",
                    check="privileged",
                    detail="컨테이너가 privileged 모드로 실행됩니다",
                    recommendation="privileged: false 설정",
                ))

            if not sc or sc.allow_privilege_escalation is not False:
                findings.append(AuditFinding(
                    container_name=container.name,
                    severity="HIGH",
                    check="allowPrivilegeEscalation",
                    detail="권한 상승이 허용되어 있습니다 (K8s 기본값)",
                    recommendation="allowPrivilegeEscalation: false 설정",
                ))

            if sc and sc.capabilities_add:
                dangerous = set(sc.capabilities_add) & _DANGEROUS_CAPS
                if dangerous:
                    findings.append(AuditFinding(
                        container_name=container.name,
                        severity="HIGH",
                        check="capabilities",
                        detail=f"위험한 capability 추가됨: {', '.join(sorted(dangerous))}",
                        recommendation="불필요한 capabilities 제거 또는 ALL drop 후 필요한 것만 add",
                    ))

            if not sc or not sc.run_as_non_root:
                findings.append(AuditFinding(
                    container_name=container.name,
                    severity="MEDIUM",
                    check="runAsNonRoot",
                    detail="root로 실행될 수 있습니다",
                    recommendation="runAsNonRoot: true 설정",
                ))

            if not sc or not sc.read_only_root_filesystem:
                findings.append(AuditFinding(
                    container_name=container.name,
                    severity="LOW",
                    check="readOnlyRootFilesystem",
                    detail="루트 파일시스템이 쓰기 가능합니다",
                    recommendation="readOnlyRootFilesystem: true 설정",
                ))

        critical_or_high = any(f.severity in ("CRITICAL", "HIGH") for f in findings)

        return AppSecurityAuditResponse(
            deployment_name=deployment.name,
            namespace=deployment.namespace,
            passed=not critical_or_high,
            findings=findings,
        )
