"""App Deployment Secret 삭제 Use Case"""

from typing import List

from fastapi import Depends

from src.api.v1.app.schemas.response import SecretDeleteResponse
from src.app.base_use_case import BaseUseCase
from src.dependencies.vault import get_vault_client
from src.infra.vault.client import VaultClient


class AppDeploymentSecretDeleteUseCase(BaseUseCase):
    """App Deployment Secret 삭제 Use Case"""

    def __init__(
        self,
        vault_client: VaultClient = Depends(get_vault_client),
    ):
        self.vault_client = vault_client

    async def __call__(
        self,
        namespace: str,
        app_name: str,
        secret_name: str,
        user_id: str
    ) -> SecretDeleteResponse:
        """App Secret 삭제 및 리소스 정리"""

        # 1. Vault Secret 삭제
        # 경로: {namespace}/{app_name}/{secret_name}
        secret_path = f"{namespace}/{app_name}/{secret_name}"
        
        await self.vault_client.delete_secret(path=secret_path)

        # 2. 남은 Secret 확인 및 리소스 정리
        # 해당 앱 폴더에 남은 Secret이 있는지 확인
        # list_path: {namespace}/{app_name}/
        remaining_secrets = await self.vault_client.list_secrets(f"{namespace}/{app_name}/")
        
        all_deleted = False
        
        # 남은 Secret이 없으면 Policy와 Role도 삭제
        if not remaining_secrets:
            policy_name = f"{namespace}-{app_name}-policy"
            role_name = f"{namespace}-{app_name}-role"
            
            # Role 삭제
            await self.vault_client.delete_kubernetes_role(role_name)
            
            # Policy 삭제
            await self.vault_client.delete_policy(policy_name)
            
            all_deleted = True

        mount_point = self.vault_client.secret_mount_point

        return SecretDeleteResponse(
            name=secret_name,
            path=f"{mount_point}/data/{secret_path}",
            all_secrets_deleted=all_deleted
        )
