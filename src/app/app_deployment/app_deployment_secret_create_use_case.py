"""App Deployment Secret 생성 Use Case"""

from fastapi import Depends

from src.api.v1.app.schemas.request import SecretCreateRequest
from src.api.v1.app.schemas.response import SecretCreateResponse
from src.app.base_use_case import BaseUseCase
from src.dependencies.kubernetes import get_deployment_repository
from src.dependencies.vault import get_vault_client
from src.infra.vault.client import VaultClient
from src.app.app.exceptions import DeploymentNotFoundException


class AppDeploymentSecretCreateUseCase(BaseUseCase):
    """App Deployment Secret 생성 Use Case"""

    def __init__(
        self,
        vault_client: VaultClient = Depends(get_vault_client),
        deployment_repository=Depends(get_deployment_repository),
    ):
        self.vault_client = vault_client
        self.deployment_repository = deployment_repository

    async def __call__(
        self,
        namespace: str,
        app_name: str,
        payload: SecretCreateRequest,
        user_id: str
    ) -> SecretCreateResponse:
        """App Secret 생성 및 권한 설정"""

        # 1. Deployment 존재 확인
        deployment = await self.deployment_repository.find_by_name(app_name, namespace)
        if not deployment:
            raise DeploymentNotFoundException(app_name, namespace)

        # 2. Vault Secret 저장
        # 경로: {namespace}/{app_name}/{secret_name}
        secret_path = f"{namespace}/{app_name}/{payload.name}"
        
        await self.vault_client.create_secret(
            path=secret_path,
            secret=payload.data
        )

        # 3. Policy 생성 (Wildcard 적용)
        # 해당 App의 모든 Secret에 접근 가능하도록 설정
        policy_name = f"{namespace}-{app_name}-policy"
        mount_point = self.vault_client.secret_mount_point
        
        # Policy Path: secret/data/{namespace}/{app_name}/*
        policy_path = f"{mount_point}/data/{namespace}/{app_name}/*"
        
        policy_hcl = f'''
path "{policy_path}" {{
  capabilities = ["read"]
}}
'''
        await self.vault_client.create_policy(policy_name, policy_hcl)

        # 4. Kubernetes Auth Role 생성/업데이트
        # Role 이름: {namespace}-{app_name}-role
        # ServiceAccount: {app_name}-sa
        role_name = f"{namespace}-{app_name}-role"
        service_account_name = f"{app_name}-sa"

        await self.vault_client.create_kubernetes_role(
            role_name=role_name,
            bound_service_account_names=[service_account_name],
            bound_service_account_namespaces=[namespace],
            policies=[policy_name]
        )

        return SecretCreateResponse(
            name=payload.name,
            namespace=namespace,
            app_name=app_name,
            path=f"{mount_point}/data/{secret_path}",
            policy_name=policy_name,
            role_name=role_name,
        )
