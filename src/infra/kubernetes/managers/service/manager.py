"""Service 리소스 관리 클래스"""

from typing import Optional, Dict, List
from kubernetes_asyncio.client import (
    V1Service,
    V1ObjectMeta,
    V1ServiceSpec,
    V1ServicePort,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger
from .exceptions import (
    ServiceCreationException,
    ServiceReadException,
    ServiceUpdateException,
    ServiceDeletionException,
    ServiceListException,
)


class ServiceManager:
    """Service 리소스를 관리하는 클래스"""

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_service(
        self,
        name: str,
        namespace: str,
        selector: Dict[str, str],
        ports: List[Dict[str, any]],
        service_type: str = "ClusterIP",
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        cluster_ip: Optional[str] = None,
        external_ips: Optional[List[str]] = None,
    ) -> V1Service:
        """Service 비동기 생성

        Args:
            name: Service 이름
            namespace: 네임스페이스
            selector: Pod 선택 레이블 (예: {"app_deployment": "myapp"})
            ports: 포트 매핑 리스트 (예: [{"port": 80, "target_port": 8080, "protocol": "TCP", "name": "http"}])
            service_type: Service 타입 (ClusterIP, NodePort, LoadBalancer, ExternalName)
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리
            cluster_ip: ClusterIP 주소 (None이면 자동 할당)
            external_ips: 외부 IP 리스트

        Returns:
            생성되거나 기존에 존재하는 V1Service 객체

        Raises:
            ServiceCreationException: Service 생성 실패 시
        """
        self.logger.info(
            f"Service 생성 시도: {name} (namespace: {namespace})"
        )

        # 이미 존재하는지 확인 (멱등성)
        existing = await self.get_service(name, namespace)
        if existing:
            self.logger.info(
                f"Service 이미 존재함: {name} (namespace: {namespace})"
            )
            return existing

        # ServicePort 객체 리스트 생성
        service_ports = []
        for port_config in ports:
            service_port = V1ServicePort(
                name=port_config.get("name"),
                port=port_config["port"],
                target_port=port_config.get("target_port", port_config["port"]),
                protocol=port_config.get("protocol", "TCP"),
                node_port=port_config.get("node_port"),
            )
            service_ports.append(service_port)

        # Service 객체 생성
        service = V1Service(
            api_version="v1",
            kind="Service",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {},
                annotations=annotations or {},
            ),
            spec=V1ServiceSpec(
                selector=selector,
                ports=service_ports,
                type=service_type,
                cluster_ip=cluster_ip,
                external_ips=external_ips,
            ),
        )

        try:
            svc = await self.k8s_client.core_v1.create_namespaced_service(
                namespace=namespace,
                body=service,
            )
            self.logger.info(
                f"Service 생성 완료: {name} (namespace: {namespace})"
            )
            return svc

        except ApiException as e:
            # 409 Conflict: 동시 요청으로 이미 생성된 경우
            if e.status == 409:
                self.logger.warning(
                    f"Service 생성 충돌 (409), 재조회: {name}"
                )
                existing = await self.get_service(name, namespace)
                if existing:
                    return existing

            self.logger.error(
                f"Service 생성 실패: {name} - {e.reason}, body: {e.body}"
            )
            raise ServiceCreationException(
                service_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Service 생성 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceCreationException(
                service_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_service(
        self,
        name: str,
        namespace: str,
    ) -> Optional[V1Service]:
        """Service 비동기 조회

        Args:
            name: Service 이름
            namespace: 네임스페이스

        Returns:
            V1Service 객체 또는 None (존재하지 않으면)

        Raises:
            ServiceReadException: 조회 실패 시 (404 제외)
        """
        try:
            svc = await self.k8s_client.core_v1.read_namespaced_service(
                name=name,
                namespace=namespace,
            )
            return svc

        except ApiException as e:
            if e.status == 404:
                return None

            self.logger.error(
                f"Service 조회 실패: {name} (namespace: {namespace}) - {e.reason}"
            )
            raise ServiceReadException(
                service_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Service 조회 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceReadException(
                service_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def delete_service(
        self,
        name: str,
        namespace: str,
        grace_period_seconds: Optional[int] = None,
    ) -> bool:
        """Service 비동기 삭제

        Args:
            name: Service 이름
            namespace: 네임스페이스
            grace_period_seconds: 유예 기간 (초)

        Returns:
            삭제 성공 여부

        Raises:
            ServiceDeletionException: 삭제 실패 시
        """
        self.logger.info(
            f"Service 삭제 시도: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_service(name, namespace)
        if not existing:
            self.logger.info(
                f"Service가 존재하지 않음: {name} (namespace: {namespace})"
            )
            return True

        try:
            await self.k8s_client.core_v1.delete_namespaced_service(
                name=name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
            )
            self.logger.info(
                f"Service 삭제 완료: {name} (namespace: {namespace})"
            )
            return True

        except ApiException as e:
            # 404: 이미 삭제된 경우
            if e.status == 404:
                self.logger.info(
                    f"Service 이미 삭제됨: {name} (namespace: {namespace})"
                )
                return True

            self.logger.error(
                f"Service 삭제 실패: {name} - {e.reason}"
            )
            raise ServiceDeletionException(
                service_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Service 삭제 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceDeletionException(
                service_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def list_services(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[V1Service]:
        """Service 목록 비동기 조회

        Args:
            namespace: 네임스페이스 (None이면 전체 조회)
            label_selector: 레이블 셀렉터 (예: "app_deployment=myapp")
            field_selector: 필드 셀렉터 (예: "metadata.name=test")

        Returns:
            V1Service 객체 리스트

        Raises:
            ServiceListException: 목록 조회 실패 시
        """
        try:
            if namespace:
                result = await self.k8s_client.core_v1.list_namespaced_service(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = await self.k8s_client.core_v1.list_service_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            return result.items

        except ApiException as e:
            self.logger.error(
                f"Service 목록 조회 실패 (namespace: {namespace}) - {e.reason}"
            )
            raise ServiceListException(
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Service 목록 조회 중 예외 발생 - {str(e)}"
            )
            raise ServiceListException(
                namespace=namespace,
                reason=str(e),
            )

    async def exists(self, name: str, namespace: str) -> bool:
        """Service 존재 여부 확인

        Args:
            name: Service 이름
            namespace: 네임스페이스

        Returns:
            존재 여부
        """
        svc = await self.get_service(name, namespace)
        return svc is not None

    async def update_labels(
        self,
        name: str,
        namespace: str,
        labels: Dict[str, str],
        merge: bool = True,
    ) -> V1Service:
        """Service 레이블 업데이트

        Args:
            name: Service 이름
            namespace: 네임스페이스
            labels: 새로운 레이블 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1Service 객체

        Raises:
            ServiceUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"Service 레이블 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_service(name, namespace)
        if not existing:
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason="Service does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.labels:
            new_labels = {**existing.metadata.labels, **labels}
        else:
            new_labels = labels

        # Patch 요청
        body = {"metadata": {"labels": new_labels}}

        try:
            svc = await self.k8s_client.core_v1.patch_namespaced_service(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"Service 레이블 업데이트 완료: {name} (namespace: {namespace})"
            )
            return svc

        except ApiException as e:
            self.logger.error(
                f"Service 레이블 업데이트 실패: {name} - {e.reason}"
            )
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Service 레이블 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_annotations(
        self,
        name: str,
        namespace: str,
        annotations: Dict[str, str],
        merge: bool = True,
    ) -> V1Service:
        """Service 어노테이션 업데이트

        Args:
            name: Service 이름
            namespace: 네임스페이스
            annotations: 새로운 어노테이션 딕셔너리
            merge: True면 병합, False면 교체

        Returns:
            업데이트된 V1Service 객체

        Raises:
            ServiceUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"Service 어노테이션 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_service(name, namespace)
        if not existing:
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason="Service does not exist",
            )

        # 병합 또는 교체
        if merge and existing.metadata.annotations:
            new_annotations = {**existing.metadata.annotations, **annotations}
        else:
            new_annotations = annotations

        # Patch 요청
        body = {"metadata": {"annotations": new_annotations}}

        try:
            svc = await self.k8s_client.core_v1.patch_namespaced_service(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"Service 어노테이션 업데이트 완료: {name} (namespace: {namespace})"
            )
            return svc

        except ApiException as e:
            self.logger.error(
                f"Service 어노테이션 업데이트 실패: {name} - {e.reason}"
            )
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Service 어노테이션 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_selector(
        self,
        name: str,
        namespace: str,
        selector: Dict[str, str],
    ) -> V1Service:
        """Service selector 업데이트

        Args:
            name: Service 이름
            namespace: 네임스페이스
            selector: 새로운 selector 딕셔너리

        Returns:
            업데이트된 V1Service 객체

        Raises:
            ServiceUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"Service selector 업데이트: {name} (namespace: {namespace})"
        )

        # 존재 여부 확인
        existing = await self.get_service(name, namespace)
        if not existing:
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason="Service does not exist",
            )

        # Patch 요청
        body = {"spec": {"selector": selector}}

        try:
            svc = await self.k8s_client.core_v1.patch_namespaced_service(
                name=name,
                namespace=namespace,
                body=body,
            )
            self.logger.info(
                f"Service selector 업데이트 완료: {name} (namespace: {namespace})"
            )
            return svc

        except ApiException as e:
            self.logger.error(
                f"Service selector 업데이트 실패: {name} - {e.reason}"
            )
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Service selector 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def update_service(
        self,
        name: str,
        namespace: str,
        selector: Optional[Dict[str, str]] = None,
        ports: Optional[List[Dict[str, any]]] = None,
        service_type: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> V1Service:
        """Service 전체 업데이트 (replace)

        Args:
            name: Service 이름
            namespace: 네임스페이스
            selector: Pod 선택 레이블
            ports: 포트 매핑 리스트
            service_type: Service 타입
            labels: 레이블 딕셔너리
            annotations: 어노테이션 딕셔너리

        Returns:
            업데이트된 V1Service 객체

        Raises:
            ServiceUpdateException: 업데이트 실패 시
        """
        self.logger.info(
            f"Service 업데이트 시도: {name} (namespace: {namespace})"
        )

        # 기존 Service 조회
        existing = await self.get_service(name, namespace)
        if not existing:
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason="Service does not exist",
            )

        # 기존 값 유지하면서 새 값으로 업데이트
        new_selector = selector if selector is not None else existing.spec.selector
        new_service_type = service_type if service_type is not None else existing.spec.type
        new_labels = labels if labels is not None else existing.metadata.labels
        new_annotations = annotations if annotations is not None else existing.metadata.annotations

        # 포트 처리
        if ports is not None:
            service_ports = []
            for port_config in ports:
                service_port = V1ServicePort(
                    name=port_config.get("name"),
                    port=port_config["port"],
                    target_port=port_config.get("target_port", port_config["port"]),
                    protocol=port_config.get("protocol", "TCP"),
                    node_port=port_config.get("nodePort"),
                )
                service_ports.append(service_port)
        else:
            service_ports = existing.spec.ports

        # Service 객체 생성 (replace용)
        service = V1Service(
            api_version="v1",
            kind="Service",
            metadata=V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=new_labels or {},
                annotations=new_annotations or {},
                resource_version=existing.metadata.resource_version,  # 필수: 낙관적 잠금
            ),
            spec=V1ServiceSpec(
                selector=new_selector,
                ports=service_ports,
                type=new_service_type,
                cluster_ip=existing.spec.cluster_ip,  # ClusterIP는 변경 불가, 기존 값 유지
            ),
        )

        try:
            svc = await self.k8s_client.core_v1.replace_namespaced_service(
                name=name,
                namespace=namespace,
                body=service,
            )
            self.logger.info(
                f"Service 업데이트 완료: {name} (namespace: {namespace})"
            )
            return svc

        except ApiException as e:
            self.logger.error(
                f"Service 업데이트 실패: {name} - {e.reason}, body: {e.body}"
            )
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason=e.reason,
                detail={"status": e.status, "body": e.body},
            )

        except Exception as e:
            self.logger.error(
                f"Service 업데이트 중 예외 발생: {name} - {str(e)}"
            )
            raise ServiceUpdateException(
                service_name=name,
                namespace=namespace,
                reason=str(e),
            )

    async def get_service_endpoints(
        self,
        name: str,
        namespace: str,
    ) -> Optional[str]:
        """Service 엔드포인트 조회

        Args:
            name: Service 이름
            namespace: 네임스페이스

        Returns:
            Service의 ClusterIP 또는 LoadBalancer IP, 존재하지 않으면 None
        """
        svc = await self.get_service(name, namespace)
        if not svc or not svc.spec:
            return None

        # LoadBalancer 타입인 경우 External IP 반환
        if svc.spec.type == "LoadBalancer" and svc.status and svc.status.load_balancer:
            ingress = svc.status.load_balancer.ingress
            if ingress and len(ingress) > 0:
                return ingress[0].ip or ingress[0].hostname

        # ClusterIP 반환
        return svc.spec.cluster_ip
