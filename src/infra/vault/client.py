"""Vault API 클라이언트 (hvac 기반)"""

from typing import Optional, Dict, List, Any
import asyncio
from functools import partial
import hvac
from hvac.exceptions import VaultError, InvalidPath

from src.common.config.vault import VAULT_CONFIG
from src.core.logger import Logger, get_logger
from .exceptions import (
    VaultRoleException,
    VaultPolicyException,
    VaultSecretException,
)

class VaultClient:
    """
    Vault API 비동기 클라이언트 (hvac 기반)

    공식 hvac SDK를 사용하여 Vault를 관리한다.
    동기 hvac 함수를 run_in_executor로 래핑하여 비동기 인터페이스를 제공한다.
    """

    def __init__(
        self,
        vault_addr: str = VAULT_CONFIG.addr,
        vault_token: Optional[str] = VAULT_CONFIG.token,
        vault_namespace: Optional[str] = VAULT_CONFIG.namespace,
        kubernetes_auth_path: str = VAULT_CONFIG.kubernetes_auth_path,
        secret_mount_point: str = VAULT_CONFIG.secret_mount_point,
        logger: Optional[Logger] = None,
    ):
        """
        VaultClient 초기화

        Args:
            vault_addr: Vault 서버 주소 (예: http://vault.default.svc.cluster.local:8200)
            vault_token: Vault 토큰 (옵션)
            vault_namespace: Vault Namespace (Enterprise 기능, 옵션)
            kubernetes_auth_path: Kubernetes Auth Mount Path
            secret_mount_point: KV Secret Engine Mount Point
            logger: 로거 인스턴스
        """
        self.vault_addr = vault_addr.rstrip("/")
        self.vault_token = vault_token
        self.vault_namespace = vault_namespace
        self.kubernetes_auth_path = kubernetes_auth_path
        self.secret_mount_point = secret_mount_point
        self.logger = logger or get_logger()

        # hvac 클라이언트 초기화
        self.client = hvac.Client(
            url=self.vault_addr,
            token=self.vault_token,
            namespace=self.vault_namespace,
        )

    async def _run_in_executor(self, func, *args, **kwargs):
        """
        동기 함수를 비동기로 실행

        Args:
            func: 실행할 함수
            *args: 위치 인자
            **kwargs: 키워드 인자

        Returns:
            함수 실행 결과
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(func, *args, **kwargs)
        )

    # ========== Kubernetes Auth Role 관리 ==========

    async def create_kubernetes_role(
        self,
        role_name: str,
        bound_service_account_names: List[str],
        bound_service_account_namespaces: List[str],
        policies: List[str],
        ttl: str = "1h",
        max_ttl: str = "24h",
    ) -> Dict[str, Any]:
        """
        Kubernetes Auth Role 생성

        Args:
            role_name: Role 이름
            bound_service_account_names: 바인딩할 ServiceAccount 이름 리스트
            bound_service_account_namespaces: 바인딩할 Namespace 리스트
            policies: 적용할 Policy 리스트
            ttl: 토큰 유효 시간
            max_ttl: 토큰 최대 유효 시간

        Returns:
            생성 결과

        Raises:
            VaultRoleException: Role 생성 실패
        """
        self.logger.info(f"Vault Kubernetes Role 생성: {role_name}")

        try:
            result = await self._run_in_executor(
                self.client.auth.kubernetes.create_role,
                name=role_name,
                bound_service_account_names=bound_service_account_names,
                bound_service_account_namespaces=bound_service_account_namespaces,
                policies=policies,
                ttl=ttl,
                max_ttl=max_ttl,
                mount_point=self.kubernetes_auth_path,
            )
            self.logger.info(f"Vault Kubernetes Role 생성 완료: {role_name}")
            return result or {}

        except VaultError as e:
            self.logger.error(f"Vault Kubernetes Role 생성 실패: {role_name} - {str(e)}")
            raise VaultRoleException(
                role_name=role_name,
                operation="생성",
                reason=str(e),
            )
        except Exception as e:
            self.logger.error(f"Vault Kubernetes Role 생성 중 예외: {role_name} - {str(e)}")
            raise VaultRoleException(
                role_name=role_name,
                operation="생성",
                reason=str(e),
            )

    async def get_kubernetes_role(self, role_name: str) -> Optional[Dict[str, Any]]:
        """
        Kubernetes Auth Role 조회

        Args:
            role_name: Role 이름

        Returns:
            Role 정보 (없으면 None)
        """
        try:
            result = await self._run_in_executor(
                self.client.auth.kubernetes.read_role,
                name=role_name,
                mount_point=self.kubernetes_auth_path,
            )
            return result.get("data") if result else None

        except InvalidPath:
            return None
        except VaultError as e:
            raise VaultRoleException(
                role_name=role_name,
                operation="조회",
                reason=str(e),
            )

    async def delete_kubernetes_role(self, role_name: str) -> bool:
        """
        Kubernetes Auth Role 삭제

        Args:
            role_name: Role 이름

        Returns:
            삭제 성공 여부
        """
        self.logger.info(f"Vault Kubernetes Role 삭제: {role_name}")

        try:
            await self._run_in_executor(
                self.client.auth.kubernetes.delete_role,
                name=role_name,
                mount_point=self.kubernetes_auth_path,
            )
            self.logger.info(f"Vault Kubernetes Role 삭제 완료: {role_name}")
            return True

        except InvalidPath:
            self.logger.info(f"Vault Kubernetes Role이 이미 없음: {role_name}")
            return True
        except VaultError as e:
            raise VaultRoleException(
                role_name=role_name,
                operation="삭제",
                reason=str(e),
            )

    async def list_kubernetes_roles(self) -> List[str]:
        """
        Kubernetes Auth Role 목록 조회

        Returns:
            Role 이름 리스트
        """
        try:
            result = await self._run_in_executor(
                self.client.auth.kubernetes.list_roles,
                mount_point=self.kubernetes_auth_path,
            )
            if result and "data" in result and "keys" in result["data"]:
                return result["data"]["keys"]
            return []

        except (InvalidPath, VaultError):
            return []

    # ========== Policy 관리 ==========

    async def create_policy(
        self,
        policy_name: str,
        policy_hcl: str,
    ) -> bool:
        """
        Vault Policy 생성

        Args:
            policy_name: Policy 이름
            policy_hcl: Policy HCL 문자열

        Returns:
            생성 성공 여부

        Example:
            policy_hcl = '''
            path "secret/data/myapp/*" {
                capabilities = ["read"]
            }
            '''
        """
        self.logger.info(f"Vault Policy 생성: {policy_name}")

        try:
            await self._run_in_executor(
                self.client.sys.create_or_update_policy,
                name=policy_name,
                policy=policy_hcl,
            )
            self.logger.info(f"Vault Policy 생성 완료: {policy_name}")
            return True

        except VaultError as e:
            self.logger.error(f"Vault Policy 생성 실패: {policy_name} - {str(e)}")
            raise VaultPolicyException(
                policy_name=policy_name,
                operation="생성",
                reason=str(e),
            )

    async def get_policy(self, policy_name: str) -> Optional[str]:
        """
        Vault Policy 조회

        Args:
            policy_name: Policy 이름

        Returns:
            Policy HCL 문자열 (없으면 None)
        """
        try:
            result = await self._run_in_executor(
                self.client.sys.read_policy,
                name=policy_name,
            )
            if result and "data" in result and "policy" in result["data"]:
                return result["data"]["policy"]
            # hvac v1.x 에서는 직접 policy 문자열 반환
            if isinstance(result, str):
                return result
            return None

        except InvalidPath:
            return None
        except VaultError as e:
            raise VaultPolicyException(
                policy_name=policy_name,
                operation="조회",
                reason=str(e),
            )

    async def delete_policy(self, policy_name: str) -> bool:
        """
        Vault Policy 삭제

        Args:
            policy_name: Policy 이름

        Returns:
            삭제 성공 여부
        """
        self.logger.info(f"Vault Policy 삭제: {policy_name}")

        try:
            await self._run_in_executor(
                self.client.sys.delete_policy,
                name=policy_name,
            )
            self.logger.info(f"Vault Policy 삭제 완료: {policy_name}")
            return True

        except InvalidPath:
            self.logger.info(f"Vault Policy가 이미 없음: {policy_name}")
            return True
        except VaultError as e:
            raise VaultPolicyException(
                policy_name=policy_name,
                operation="삭제",
                reason=str(e),
            )

    async def list_policies(self) -> List[str]:
        """
        Vault Policy 목록 조회

        Returns:
            Policy 이름 리스트
        """
        try:
            result = await self._run_in_executor(
                self.client.sys.list_policies,
            )
            if result and "data" in result and "policies" in result["data"]:
                return result["data"]["policies"]
            # hvac v1.x 에서는 직접 리스트 반환
            if isinstance(result, list):
                return result
            return []

        except (InvalidPath, VaultError):
            return []

    # ========== Health Check ==========

    async def health_check(self) -> bool:
        """
        Vault 서버 health check

        Returns:
            정상 여부
        """
        try:
            result = await self._run_in_executor(
                self.client.sys.read_health_status,
            )
            return result is not None

        except Exception:
            return False

    # ========== Secret 관리 (KV v2) ==========

    async def create_secret(
        self,
        path: str,
        secret: Dict[str, Any],
        mount_point: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Vault에 Secret 생성 또는 업데이트

        Args:
            path: Secret 경로 (예: "myapp/db")
            secret: Secret 데이터 (예: {"username": "admin", "password": "secret"})
            mount_point: KV 마운트 포인트 (None이면 config 값 사용)

        Returns:
            생성 결과

        Raises:
            VaultSecretException: Secret 생성 실패

        Example:
            >>> await vault_client.create_secret(
            ...     path="myapp/db",
            ...     secret={"username": "admin", "password": "Hashi123"}
            ... )
        """
        mount_point = mount_point or self.secret_mount_point
        self.logger.info(f"Vault Secret 생성: {mount_point}/data/{path}")

        try:
            result = await self._run_in_executor(
                self.client.secrets.kv.v2.create_or_update_secret,
                path=path,
                secret=secret,
                mount_point=mount_point,
            )
            self.logger.info(f"Vault Secret 생성 완료: {mount_point}/data/{path}")
            return result or {}

        except VaultError as e:
            self.logger.error(f"Vault Secret 생성 실패: {path} - {str(e)}")
            raise VaultSecretException(
                secret_path=f"{mount_point}/data/{path}",
                operation="생성",
                reason=str(e),
            )

    async def get_secret(
        self,
        path: str,
        mount_point: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Vault에서 Secret 조회

        Args:
            path: Secret 경로 (예: "myapp/db")
            mount_point: KV 마운트 포인트 (None이면 config 값 사용)
            version: Secret 버전 (None이면 최신 버전)

        Returns:
            Secret 데이터 (없으면 None)

        Example:
            >>> secret = await vault_client.get_secret("myapp/db")
            >>> print(secret)
            {'username': 'admin', 'password': 'Hashi123'}
        """
        mount_point = mount_point or self.secret_mount_point
        try:
            result = await self._run_in_executor(
                self.client.secrets.kv.v2.read_secret_version,
                path=path,
                version=version,
                mount_point=mount_point,
            )
            if result and "data" in result and "data" in result["data"]:
                return result["data"]["data"]
            return None

        except InvalidPath:
            return None
        except VaultError as e:
            raise VaultSecretException(
                secret_path=f"{mount_point}/data/{path}",
                operation="조회",
                reason=str(e),
            )

    async def patch_secret(
        self,
        path: str,
        data: Dict[str, Any],
        mount_point: Optional[str] = None,
    ) -> Dict[str, Any]:
        """기존 Secret에 데이터를 병합하여 저장 (없으면 새로 생성)"""
        existing = await self.get_secret(path, mount_point) or {}
        return await self.create_secret(path, {**existing, **data}, mount_point)

    async def remove_secret_key(
        self,
        path: str,
        key: str,
        mount_point: Optional[str] = None,
    ) -> bool:
        """Secret에서 특정 키만 제거하고 나머지는 유지"""
        existing = await self.get_secret(path, mount_point)
        if existing is None or key not in existing:
            return False
        updated = {k: v for k, v in existing.items() if k != key}
        await self.create_secret(path, updated, mount_point)
        return True

    async def delete_secret(
        self,
        path: str,
        mount_point: Optional[str] = None,
    ) -> bool:
        """
        Vault에서 Secret 삭제 (모든 버전 삭제)

        Args:
            path: Secret 경로 (예: "myapp/db")
            mount_point: KV 마운트 포인트 (None이면 config 값 사용)

        Returns:
            삭제 성공 여부
        """
        mount_point = mount_point or self.secret_mount_point
        self.logger.info(f"Vault Secret 삭제: {mount_point}/data/{path}")

        try:
            await self._run_in_executor(
                self.client.secrets.kv.v2.delete_metadata_and_all_versions,
                path=path,
                mount_point=mount_point,
            )
            self.logger.info(f"Vault Secret 삭제 완료: {mount_point}/data/{path}")
            return True

        except InvalidPath:
            self.logger.info(f"Vault Secret이 이미 없음: {mount_point}/data/{path}")
            return True
        except VaultError as e:
            raise VaultSecretException(
                secret_path=f"{mount_point}/data/{path}",
                operation="삭제",
                reason=str(e),
            )

    async def list_secrets(
        self,
        path: str = "",
        mount_point: Optional[str] = None,
    ) -> List[str]:
        """
        Vault에서 Secret 목록 조회

        Args:
            path: 디렉토리 경로 (예: "myapp/")
            mount_point: KV 마운트 포인트 (None이면 config 값 사용)

        Returns:
            Secret 이름 리스트

        Example:
            >>> secrets = await vault_client.list_secrets("myapp/")
            >>> print(secrets)
            ['db', 'api-key', 'jwt-secret']
        """
        mount_point = mount_point or self.secret_mount_point
        try:
            result = await self._run_in_executor(
                self.client.secrets.kv.v2.list_secrets,
                path=path,
                mount_point=mount_point,
            )
            if result and "data" in result and "keys" in result["data"]:
                return result["data"]["keys"]
            return []

        except (InvalidPath, VaultError):
            return []

    # ========== Policy HCL 생성 헬퍼 ==========

    @staticmethod
    def generate_policy_hcl(
        secret_paths: List[str],
        capabilities: List[str] = ["read"],
    ) -> str:
        """
        Policy HCL 생성 헬퍼

        Args:
            secret_paths: Secret 경로 리스트
            capabilities: 권한 리스트

        Returns:
            Policy HCL 문자열

        Example:
            >>> VaultClient.generate_policy_hcl(
            ...     secret_paths=["secret/data/myapp/db"],
            ...     capabilities=["read"]
            ... )
            'path "secret/data/myapp/db" {\\n  capabilities = ["read"]\\n}\\n'
        """
        policy_lines = []

        for path in secret_paths:
            capabilities_str = str(capabilities).replace("'", '"')
            policy_lines.append(
                f'path "{path}" {{\n'
                f'  capabilities = {capabilities_str}\n'
                f'}}'
            )

        return "\n\n".join(policy_lines)
