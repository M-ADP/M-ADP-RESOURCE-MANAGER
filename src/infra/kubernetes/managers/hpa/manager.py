"""HPA 리소스 관리 클래스"""

from typing import Optional, List

from kubernetes_asyncio.client import (
    V2HorizontalPodAutoscaler,
    V2HorizontalPodAutoscalerSpec,
    V2CrossVersionObjectReference,
    V2MetricSpec,
    V2ResourceMetricSource,
    V2MetricTarget,
)
from kubernetes_asyncio.client.exceptions import ApiException

from src.infra.kubernetes.client import KubernetesClientImpl
from src.core.logger import Logger, get_logger


class HpaManager:
    """HPA 리소스를 관리하는 클래스"""

    def __init__(
        self,
        k8s_client: KubernetesClientImpl,
        logger: Optional[Logger] = None,
    ):
        self.k8s_client = k8s_client
        self.logger = logger or get_logger()

    async def create_hpa(
        self,
        name: str,
        namespace: str,
        target_ref_name: str,
        target_ref_kind: str,
        target_ref_api_version: str,
        min_replicas: int,
        max_replicas: int,
        metrics: List[dict],
        labels: Optional[dict] = None,
        annotations: Optional[dict] = None,
    ) -> V2HorizontalPodAutoscaler:
        """HPA 생성 (이미 존재하면 업데이트)"""
        self.logger.info(f"HPA 생성 시도: {name} (namespace: {namespace})")

        # 메트릭 스펙 구성
        metric_specs = self._build_metric_specs(metrics)

        hpa = V2HorizontalPodAutoscaler(
            api_version="autoscaling/v2",
            kind="HorizontalPodAutoscaler",
            metadata={
                "name": name,
                "namespace": namespace,
                "labels": labels or {},
                "annotations": annotations or {},
            },
            spec=V2HorizontalPodAutoscalerSpec(
                scale_target_ref=V2CrossVersionObjectReference(
                    api_version=target_ref_api_version,
                    kind=target_ref_kind,
                    name=target_ref_name,
                ),
                min_replicas=min_replicas,
                max_replicas=max_replicas,
                metrics=metric_specs,
            ),
        )

        try:
            # 이미 존재하는지 확인
            existing = await self.get_hpa(name, namespace)
            if existing:
                self.logger.info(f"HPA 이미 존재함: {name}. 업데이트 수행.")
                return await self.update_hpa(
                    name=name,
                    namespace=namespace,
                    target_ref_name=target_ref_name,
                    target_ref_kind=target_ref_kind,
                    target_ref_api_version=target_ref_api_version,
                    min_replicas=min_replicas,
                    max_replicas=max_replicas,
                    metrics=metrics,
                    labels=labels,
                    annotations=annotations,
                )

            result = await self.k8s_client.autoscaling_v2.create_namespaced_horizontal_pod_autoscaler(
                namespace=namespace,
                body=hpa,
            )
            self.logger.info(f"HPA 생성 완료: {name}")
            return result
        except ApiException as e:
            if e.status == 409:  # 이미 존재
                self.logger.info(f"HPA 이미 존재 (409): {name}. 업데이트 수행.")
                return await self.update_hpa(
                    name=name,
                    namespace=namespace,
                    target_ref_name=target_ref_name,
                    target_ref_kind=target_ref_kind,
                    target_ref_api_version=target_ref_api_version,
                    min_replicas=min_replicas,
                    max_replicas=max_replicas,
                    metrics=metrics,
                    labels=labels,
                    annotations=annotations,
                )
            self.logger.error(f"HPA 생성 실패: {name} - {e.reason}")
            raise
        except Exception as e:
            self.logger.error(f"HPA 생성 중 예외 발생: {name} - {str(e)}")
            raise

    async def get_hpa(self, name: str, namespace: str) -> Optional[V2HorizontalPodAutoscaler]:
        """HPA 조회"""
        try:
            return await self.k8s_client.autoscaling_v2.read_namespaced_horizontal_pod_autoscaler(
                name=name,
                namespace=namespace,
            )
        except ApiException as e:
            if e.status == 404:
                return None
            self.logger.error(f"HPA 조회 실패: {name} - {e.reason}")
            raise

    async def list_hpas(self, namespace: str) -> List[V2HorizontalPodAutoscaler]:
        """네임스페이스의 모든 HPA 목록 조회"""
        try:
            result = await self.k8s_client.autoscaling_v2.list_namespaced_horizontal_pod_autoscaler(
                namespace=namespace,
            )
            return result.items
        except ApiException as e:
            self.logger.error(f"HPA 목록 조회 실패 (namespace: {namespace}) - {e.reason}")
            raise

    async def update_hpa(
        self,
        name: str,
        namespace: str,
        target_ref_name: str,
        target_ref_kind: str,
        target_ref_api_version: str,
        min_replicas: int,
        max_replicas: int,
        metrics: List[dict],
        labels: Optional[dict] = None,
        annotations: Optional[dict] = None,
    ) -> V2HorizontalPodAutoscaler:
        """HPA 업데이트"""
        self.logger.info(f"HPA 업데이트 시도: {name} (namespace: {namespace})")

        metric_specs = self._build_metric_specs(metrics)

        hpa = V2HorizontalPodAutoscaler(
            api_version="autoscaling/v2",
            kind="HorizontalPodAutoscaler",
            metadata={
                "name": name,
                "namespace": namespace,
                "labels": labels or {},
                "annotations": annotations or {},
            },
            spec=V2HorizontalPodAutoscalerSpec(
                scale_target_ref=V2CrossVersionObjectReference(
                    api_version=target_ref_api_version,
                    kind=target_ref_kind,
                    name=target_ref_name,
                ),
                min_replicas=min_replicas,
                max_replicas=max_replicas,
                metrics=metric_specs,
            ),
        )

        try:
            result = await self.k8s_client.autoscaling_v2.replace_namespaced_horizontal_pod_autoscaler(
                name=name,
                namespace=namespace,
                body=hpa,
            )
            self.logger.info(f"HPA 업데이트 완료: {name}")
            return result
        except ApiException as e:
            self.logger.error(f"HPA 업데이트 실패: {name} - {e.reason}")
            raise
        except Exception as e:
            self.logger.error(f"HPA 업데이트 중 예외 발생: {name} - {str(e)}")
            raise

    async def delete_hpa(self, name: str, namespace: str) -> bool:
        """HPA 삭제"""
        self.logger.info(f"HPA 삭제 시도: {name} (namespace: {namespace})")
        try:
            await self.k8s_client.autoscaling_v2.delete_namespaced_horizontal_pod_autoscaler(
                name=name,
                namespace=namespace,
            )
            self.logger.info(f"HPA 삭제 완료: {name}")
            return True
        except ApiException as e:
            if e.status == 404:
                self.logger.info(f"HPA 이미 삭제됨: {name}")
                return True
            self.logger.error(f"HPA 삭제 실패: {name} - {e.reason}")
            raise
        except Exception as e:
            self.logger.error(f"HPA 삭제 중 예외 발생: {name} - {str(e)}")
            raise

    def _build_metric_specs(self, metrics: List[dict]) -> List[V2MetricSpec]:
        """메트릭 스펙 리스트 구성"""
        metric_specs = []
        for m in metrics:
            if m.get("type") == "Resource":
                metric_spec = V2MetricSpec(
                    type="Resource",
                    resource=V2ResourceMetricSource(
                        name=m.get("resource_name"),
                        target=V2MetricTarget(
                            type=m.get("target_type"),
                            average_utilization=m.get("target_value") if m.get("target_type") == "Utilization" else None,
                            average_value=str(m.get("target_value")) if m.get("target_type") == "AverageValue" else None,
                        ),
                    ),
                )
                metric_specs.append(metric_spec)
        return metric_specs
