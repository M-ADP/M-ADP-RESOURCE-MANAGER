"""Secret 접근 관리 클래스 (Vault 기반)"""

from typing import Optional, Dict, List, Any
from kubernetes_asyncio.client import V1ServiceAccount, V1Deployment, V1StatefulSet

from infra.kubernetes.client import KubernetesClient
from infra.vault.client import VaultClient
from core.logger import Logger, get_logger
from .exceptions import (
    SecretAccessBindingException,
    SecretAccessUnbindingException,
    VaultInjectionException,
)


class SecretManager:
    """
    Vault 기반 Secret 접근 구조 관리 클래스
    
    이 클래스는 Kubernetes Secret 리소스를 직접 생성하지 않는다.
    대신 Vault와의 연동 구조를 관리한다:
    - Vault Role/Policy 생성
    - ServiceAccount ↔ Vault 바인딩
    - Workload에 Vault Agent/CSI 설정 주입
    
    실제 Secret 값은 Vault에만 존재한다.
    """

    # Vault 관련 annotation keys
    VAULT_ROLE_ANNOTATION = "vault.hashicorp.com/role"
    VAULT_AGENT_INJECT_ANNOTATION = "vault.hashicorp.com/agent-inject"
    VAULT_AGENT_INJECT_SECRET_PREFIX = "vault.hashicorp.com/agent-inject-secret-"

    def __init__(
        self,
        k8s_client: KubernetesClient,
        vault_client: VaultClient,
        logger: Optional[Logger] = None,
    ):
        """
        SecretManager 초기화
        
        Args:
            k8s_client: Kubernetes API 클라이언트
            vault_client: Vault API 클라이언트
            logger: 로거 인스턴스
        """
        self.k8s_client = k8s_client
        self.vault_client = vault_client
        self.logger = logger or get_logger()

    # ========== Vault Role 관리 ==========

    async def create_vault_role(
        self,
        role_name: str,
        bound_service_account_names: List[str],
        bound_service_account_namespaces: List[str],
        policies: List[str],
        ttl: str = "1h",
        max_ttl: str = "24h",
    ) -> Dict[str, Any]:
        """
        Vault Kubernetes Auth Role 생성
        
        Args:
            role_name: Vault Role 이름
            bound_service_account_names: 바인딩할 ServiceAccount 이름 리스트
            bound_service_account_namespaces: 바인딩할 Namespace 리스트
            policies: 적용할 Vault Policy 리스트
            ttl: Token 유효 시간
            max_ttl: Token 최대 유효 시간
            
        Returns:
            생성된 Vault Role 정보
        """
        return await self.vault_client.create_kubernetes_role(
            role_name=role_name,
            bound_service_account_names=bound_service_account_names,
            bound_service_account_namespaces=bound_service_account_namespaces,
            policies=policies,
            ttl=ttl,
            max_ttl=max_ttl,
        )

    async def get_vault_role(self, role_name: str) -> Optional[Dict[str, Any]]:
        """Vault Role 조회"""
        return await self.vault_client.get_kubernetes_role(role_name)

    async def delete_vault_role(self, role_name: str) -> bool:
        """Vault Role 삭제"""
        return await self.vault_client.delete_kubernetes_role(role_name)

    async def list_vault_roles(self) -> List[str]:
        """Vault Role 목록 조회"""
        return await self.vault_client.list_kubernetes_roles()

    # ========== Vault Policy 관리 ==========

    async def create_vault_policy(
        self,
        policy_name: str,
        secret_paths: List[str],
        capabilities: List[str] = ["read"],
    ) -> bool:
        """
        Vault Policy 생성
        
        Args:
            policy_name: Policy 이름
            secret_paths: 접근 가능한 Secret 경로 리스트
                         예: ["secret/data/app/db-credentials"]
            capabilities: 권한 리스트 (read, create, update, delete 등)
            
        Returns:
            생성 성공 여부
        """
        # Policy HCL 생성
        policy_hcl = self.vault_client.generate_policy_hcl(
            secret_paths=secret_paths,
            capabilities=capabilities,
        )
        
        return await self.vault_client.create_policy(
            policy_name=policy_name,
            policy_hcl=policy_hcl,
        )

    async def get_vault_policy(self, policy_name: str) -> Optional[str]:
        """Vault Policy 조회"""
        return await self.vault_client.get_policy(policy_name)

    async def delete_vault_policy(self, policy_name: str) -> bool:
        """Vault Policy 삭제"""
        return await self.vault_client.delete_policy(policy_name)

    async def list_vault_policies(self) -> List[str]:
        """Vault Policy 목록 조회"""
        return await self.vault_client.list_policies()

    # ========== ServiceAccount ↔ Vault 바인딩 ==========

    async def bind_serviceaccount_to_vault(
        self,
        service_account_name: str,
        namespace: str,
        vault_role_name: str,
        secret_paths: List[str],
        capabilities: List[str] = ["read"],
    ) -> Dict[str, Any]:
        """
        ServiceAccount를 Vault Role에 바인딩
        
        이 메서드는 내부적으로:
        1. Vault Policy 생성 (secret_paths 기반)
        2. Vault Role 생성 (ServiceAccount와 Policy 연결)
        3. ServiceAccount에 annotation 추가
        
        Args:
            service_account_name: ServiceAccount 이름
            namespace: Namespace
            vault_role_name: 생성할 Vault Role 이름
            secret_paths: 접근 가능한 Secret 경로 리스트
            capabilities: 권한 리스트
            
        Returns:
            바인딩 정보
            {
                "vault_role": "...",
                "vault_policy": "...",
                "service_account": "...",
                "secret_paths": [...]
            }
            
        Raises:
            SecretAccessBindingException: 바인딩 실패 시
        """
        self.logger.info(
            f"ServiceAccount를 Vault에 바인딩: {namespace}/{service_account_name} → {vault_role_name}"
        )

        try:
            # 1. Policy 생성
            policy_name = f"{namespace}-{service_account_name}-policy"
            await self.create_vault_policy(
                policy_name=policy_name,
                secret_paths=secret_paths,
                capabilities=capabilities,
            )
            self.logger.info(f"Vault Policy 생성 완료: {policy_name}")

            # 2. Vault Role 생성
            await self.create_vault_role(
                role_name=vault_role_name,
                bound_service_account_names=[service_account_name],
                bound_service_account_namespaces=[namespace],
                policies=[policy_name],
            )
            self.logger.info(f"Vault Role 생성 완료: {vault_role_name}")

            # 3. ServiceAccount에 annotation 추가
            annotation_key = self.VAULT_ROLE_ANNOTATION
            annotation_value = vault_role_name

            sa_patch = {
                "metadata": {
                    "annotations": {
                        annotation_key: annotation_value,
                    }
                }
            }

            await self.k8s_client.core_v1.patch_namespaced_service_account(
                name=service_account_name,
                namespace=namespace,
                body=sa_patch,
            )
            self.logger.info(
                f"ServiceAccount annotation 추가 완료: {namespace}/{service_account_name}"
            )

            return {
                "vault_role": vault_role_name,
                "vault_policy": policy_name,
                "service_account": f"{namespace}/{service_account_name}",
                "secret_paths": secret_paths,
            }

        except Exception as e:
            self.logger.error(
                f"ServiceAccount Vault 바인딩 실패: {namespace}/{service_account_name} - {str(e)}"
            )
            raise SecretAccessBindingException(
                service_account_name=service_account_name,
                namespace=namespace,
                reason=str(e),
                detail={"vault_role": vault_role_name},
            )

    async def unbind_serviceaccount_from_vault(
        self,
        service_account_name: str,
        namespace: str,
    ) -> bool:
        """
        ServiceAccount의 Vault 바인딩 해제
        
        Args:
            service_account_name: ServiceAccount 이름
            namespace: Namespace
            
        Returns:
            바인딩 해제 성공 여부
            
        Raises:
            SecretAccessUnbindingException: 바인딩 해제 실패 시
        """
        self.logger.info(
            f"ServiceAccount Vault 바인딩 해제: {namespace}/{service_account_name}"
        )

        try:
            # 1. ServiceAccount에서 annotation 읽기
            sa = await self.k8s_client.core_v1.read_namespaced_service_account(
                name=service_account_name,
                namespace=namespace,
            )

            if not sa.metadata.annotations:
                self.logger.info("바인딩된 Vault Role이 없음")
                return True

            vault_role_name = sa.metadata.annotations.get(self.VAULT_ROLE_ANNOTATION)
            if not vault_role_name:
                self.logger.info("바인딩된 Vault Role이 없음")
                return True

            # 2. Vault Role 삭제
            await self.delete_vault_role(vault_role_name)
            self.logger.info(f"Vault Role 삭제 완료: {vault_role_name}")

            # 3. Vault Policy 삭제
            policy_name = f"{namespace}-{service_account_name}-policy"
            await self.delete_vault_policy(policy_name)
            self.logger.info(f"Vault Policy 삭제 완료: {policy_name}")

            # 4. ServiceAccount annotation 제거
            sa_patch = {
                "metadata": {
                    "annotations": {
                        self.VAULT_ROLE_ANNOTATION: None,
                    }
                }
            }

            await self.k8s_client.core_v1.patch_namespaced_service_account(
                name=service_account_name,
                namespace=namespace,
                body=sa_patch,
            )
            self.logger.info(
                f"ServiceAccount annotation 제거 완료: {namespace}/{service_account_name}"
            )

            return True

        except Exception as e:
            self.logger.error(
                f"ServiceAccount Vault 바인딩 해제 실패: {namespace}/{service_account_name} - {str(e)}"
            )
            raise SecretAccessUnbindingException(
                service_account_name=service_account_name,
                namespace=namespace,
                reason=str(e),
            )

    # ========== Workload에 Vault 설정 주입 ==========

    async def inject_vault_agent_to_deployment(
        self,
        deployment_name: str,
        namespace: str,
        vault_role: str,
        secret_configs: List[Dict[str, str]],
    ) -> V1Deployment:
        """
        Deployment에 Vault Agent Injector annotations 추가
        
        Args:
            deployment_name: Deployment 이름
            namespace: Namespace
            vault_role: 사용할 Vault Role
            secret_configs: Secret 설정 리스트
                [
                    {"name": "db-creds", "path": "secret/data/app/db"},
                    {"name": "api-key", "path": "secret/data/app/api"},
                ]
            
        Returns:
            업데이트된 Deployment
            
        Raises:
            VaultInjectionException: 주입 실패 시
        """
        self.logger.info(
            f"Deployment에 Vault Agent 설정 주입: {namespace}/{deployment_name}"
        )

        try:
            # Annotations 생성
            annotations = {
                self.VAULT_AGENT_INJECT_ANNOTATION: "true",
                self.VAULT_ROLE_ANNOTATION: vault_role,
            }

            # Secret별 annotation 추가
            for secret_config in secret_configs:
                secret_name = secret_config["name"]
                secret_path = secret_config["path"]
                annotation_key = f"{self.VAULT_AGENT_INJECT_SECRET_PREFIX}{secret_name}"
                annotations[annotation_key] = secret_path

            # Deployment patch
            patch = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": annotations
                        }
                    }
                }
            }

            deployment = await self.k8s_client.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=patch,
            )

            self.logger.info(
                f"Deployment Vault Agent 설정 주입 완료: {namespace}/{deployment_name}"
            )

            return deployment

        except Exception as e:
            self.logger.error(
                f"Deployment Vault Agent 설정 주입 실패: {namespace}/{deployment_name} - {str(e)}"
            )
            raise VaultInjectionException(
                workload_name=deployment_name,
                workload_type="Deployment",
                namespace=namespace,
                reason=str(e),
            )

    async def inject_vault_agent_to_statefulset(
        self,
        statefulset_name: str,
        namespace: str,
        vault_role: str,
        secret_configs: List[Dict[str, str]],
    ) -> V1StatefulSet:
        """
        StatefulSet에 Vault Agent Injector annotations 추가
        
        Args:
            statefulset_name: StatefulSet 이름
            namespace: Namespace
            vault_role: 사용할 Vault Role
            secret_configs: Secret 설정 리스트
            
        Returns:
            업데이트된 StatefulSet
        """
        self.logger.info(
            f"StatefulSet에 Vault Agent 설정 주입: {namespace}/{statefulset_name}"
        )

        try:
            # Annotations 생성
            annotations = {
                self.VAULT_AGENT_INJECT_ANNOTATION: "true",
                self.VAULT_ROLE_ANNOTATION: vault_role,
            }

            # Secret별 annotation 추가
            for secret_config in secret_configs:
                secret_name = secret_config["name"]
                secret_path = secret_config["path"]
                annotation_key = f"{self.VAULT_AGENT_INJECT_SECRET_PREFIX}{secret_name}"
                annotations[annotation_key] = secret_path

            # StatefulSet patch
            patch = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": annotations
                        }
                    }
                }
            }

            statefulset = await self.k8s_client.apps_v1.patch_namespaced_stateful_set(
                name=statefulset_name,
                namespace=namespace,
                body=patch,
            )

            self.logger.info(
                f"StatefulSet Vault Agent 설정 주입 완료: {namespace}/{statefulset_name}"
            )

            return statefulset

        except Exception as e:
            self.logger.error(
                f"StatefulSet Vault Agent 설정 주입 실패: {namespace}/{statefulset_name} - {str(e)}"
            )
            raise VaultInjectionException(
                workload_name=statefulset_name,
                workload_type="StatefulSet",
                namespace=namespace,
                reason=str(e),
            )

    # ========== 통합 헬퍼 메서드 ==========

    async def setup_secret_access(
        self,
        service_account_name: str,
        namespace: str,
        secret_paths: List[str],
        workload_name: Optional[str] = None,
        workload_type: Optional[str] = None,  # "deployment" or "statefulset"
        secret_configs: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Secret 접근을 위한 전체 설정 수행
        
        이 메서드는 한 번의 호출로:
        1. Vault Policy 생성
        2. Vault Role 생성
        3. ServiceAccount 바인딩
        4. (선택적) Workload에 Vault 설정 주입
        
        Args:
            service_account_name: ServiceAccount 이름
            namespace: Namespace
            secret_paths: 접근 가능한 Secret 경로 리스트
            workload_name: (선택) Workload 이름
            workload_type: (선택) Workload 타입 ("deployment" or "statefulset")
            secret_configs: (선택) Workload에 주입할 Secret 설정
            
        Returns:
            설정 결과
            {
                "vault_role": "...",
                "vault_policy": "...",
                "service_account": "...",
                "workload_updated": true/false
            }
        """
        vault_role_name = f"{namespace}-{service_account_name}-role"

        # 1. ServiceAccount를 Vault에 바인딩
        binding_result = await self.bind_serviceaccount_to_vault(
            service_account_name=service_account_name,
            namespace=namespace,
            vault_role_name=vault_role_name,
            secret_paths=secret_paths,
        )

        result = {
            **binding_result,
            "workload_updated": False,
        }

        # 2. (선택적) Workload에 Vault 설정 주입
        if workload_name and workload_type and secret_configs:
            if workload_type.lower() == "deployment":
                await self.inject_vault_agent_to_deployment(
                    deployment_name=workload_name,
                    namespace=namespace,
                    vault_role=vault_role_name,
                    secret_configs=secret_configs,
                )
                result["workload_updated"] = True
            elif workload_type.lower() == "statefulset":
                await self.inject_vault_agent_to_statefulset(
                    statefulset_name=workload_name,
                    namespace=namespace,
                    vault_role=vault_role_name,
                    secret_configs=secret_configs,
                )
                result["workload_updated"] = True

        return result

    async def teardown_secret_access(
        self,
        service_account_name: str,
        namespace: str,
    ) -> bool:
        """
        Secret 접근 설정 전체 제거
        
        Args:
            service_account_name: ServiceAccount 이름
            namespace: Namespace
            
        Returns:
            제거 성공 여부
        """
        return await self.unbind_serviceaccount_from_vault(
            service_account_name=service_account_name,
            namespace=namespace,
        )
