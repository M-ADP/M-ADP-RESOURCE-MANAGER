"""App 수정 Use Case"""

import re
from typing import Optional, Dict

from fastapi import Depends

from src.api.v1.app.schemas.request import AppRevisionRequest
from src.api.v1.app.schemas.response import (
    AppRevisionResponse,
    ContainerResourceInfo,
    ContainerResourcesInfo,
    PvcInfo,
)
from src.app.base_use_case import BaseUseCase
from src.core.exceptions import BadRequestException
from src.dependencies.kubernetes import get_deployment_repository, get_pvc_repository


def parse_size_to_bytes(size_str: str) -> int:
    """크기 문자열을 바이트로 변환 (예: 1Gi -> 1073741824)"""
    units = {
        'Ki': 1024,
        'Mi': 1024 ** 2,
        'Gi': 1024 ** 3,
        'Ti': 1024 ** 4,
        'K': 1000,
        'M': 1000 ** 2,
        'G': 1000 ** 3,
        'T': 1000 ** 4,
    }

    match = re.match(r'^(\d+(?:\.\d+)?)\s*([A-Za-z]*)$', size_str.strip())
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")

    value = float(match.group(1))
    unit = match.group(2)

    if unit == '':
        return int(value)

    if unit not in units:
        raise ValueError(f"Unknown unit: {unit}")

    return int(value * units[unit])


class AppRevisionUseCase(BaseUseCase):
    """App(Deployment) 리소스 수정 Use Case"""

    def __init__(
            self,
            deployment_repository=Depends(get_deployment_repository),
            pvc_repository=Depends(get_pvc_repository),
    ):
        self.deployment_repository = deployment_repository
        self.pvc_repository = pvc_repository

    async def __call__(
            self,
            name: str,
            namespace: str,
            payload: AppRevisionRequest,
            user_id: str
    ) -> AppRevisionResponse:
        """App(Deployment) 리소스 수정"""

        # 기존 Deployment 조회
        existing = await self.deployment_repository.find_by_name(name, namespace)
        if not existing:
            raise BadRequestException(detail=f"Deployment '{name}' not found in namespace '{namespace}'")

        # 컨테이너 이름 결정
        containers = existing.containers
        if not containers:
            raise BadRequestException(detail="No containers found in deployment")

        container_name = payload.container_name or containers[0].name

        # 리소스 업데이트
        requests_dict: Optional[Dict[str, str]] = None
        limits_dict: Optional[Dict[str, str]] = None

        if payload.requests:
            requests_dict = {}
            if payload.requests.cpu:
                requests_dict["cpu"] = payload.requests.cpu
            if payload.requests.memory:
                requests_dict["memory"] = payload.requests.memory

        if payload.limits:
            limits_dict = {}
            if payload.limits.cpu:
                limits_dict["cpu"] = payload.limits.cpu
            if payload.limits.memory:
                limits_dict["memory"] = payload.limits.memory

        # 리소스 업데이트 실행
        if requests_dict or limits_dict:
            await self.deployment_repository.update_container_resources(
                name=name,
                namespace=namespace,
                container_name=container_name,
                requests=requests_dict,
                limits=limits_dict,
            )

        # PVC 크기 수정 (증가만 가능)
        pvc_info: Optional[PvcInfo] = None
        if payload.disk:
            # 컨테이너에 연결된 PVC 찾기
            pvc_name = f"{name}-{container_name}-pvc"
            existing_pvc = await self.pvc_repository.find_by_name(pvc_name, namespace)

            if not existing_pvc:
                raise BadRequestException(
                    detail=f"PVC '{pvc_name}' not found. Disk was not configured for this container."
                )

            # 현재 크기 확인
            current_size = existing_pvc.storage
            current_bytes = parse_size_to_bytes(current_size)
            new_bytes = parse_size_to_bytes(payload.disk.size)

            if new_bytes < current_bytes:
                raise BadRequestException(
                    detail=f"Disk size can only be increased. Current: {current_size}, Requested: {payload.disk.size}"
                )

            if new_bytes > current_bytes:
                # PVC 크기 증가
                updated_pvc = await self.pvc_repository.resize(
                    name=pvc_name,
                    namespace=namespace,
                    new_storage=payload.disk.size,
                )

                # 마운트 경로 찾기
                mount_path = "/data"
                for c in containers:
                    if c.name == container_name and c.volume_mounts:
                        for vm in c.volume_mounts:
                            if vm.get("name") == f"{container_name}-volume":
                                mount_path = vm.get("mount_path", "/data")
                                break

                pvc_info = PvcInfo(
                    name=pvc_name,
                    size=payload.disk.size,
                    mount_path=mount_path,
                    storage_class=updated_pvc.storage_class_name,
                    phase=updated_pvc.phase,
                )

        # 레플리카 업데이트
        if payload.replicas is not None:
            await self.deployment_repository.update_replicas(
                name=name,
                namespace=namespace,
                replicas=payload.replicas,
            )

        # 최신 상태 조회
        updated = await self.deployment_repository.find_by_name(name, namespace)

        # 수정된 컨테이너 리소스 정보 추출
        updated_container = None
        for c in updated.containers:
            if c.name == container_name:
                updated_container = c
                break

        resources_info = ContainerResourcesInfo()
        if updated_container and updated_container.resources:
            res = updated_container.resources
            if res.get("requests"):
                resources_info.requests = ContainerResourceInfo(
                    cpu=res["requests"].get("cpu"),
                    memory=res["requests"].get("memory"),
                )
            if res.get("limits"):
                resources_info.limits = ContainerResourceInfo(
                    cpu=res["limits"].get("cpu"),
                    memory=res["limits"].get("memory"),
                )

        return AppRevisionResponse(
            name=updated.name,
            namespace=updated.namespace,
            replicas=updated.replicas,
            container_name=container_name,
            resources=resources_info,
            pvc=pvc_info,
        )
