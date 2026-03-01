from typing import Literal, Optional
from fastapi import APIRouter, Depends, Query

from src.api.infra.proxmox.schema import (
    # Cluster Resources (권장)
    ClusterNodeResource,
    ClusterNodesResponse,
    ClusterVMResource,
    ClusterVMsResponse,
    NodeStorageResource,
    NodeStoragesResponse,
    # Legacy
    NodeListResponse,
    NodeStatusResponse,
    NodeCpuInfo,
    NodeMemoryInfo,
    NodeSwapInfo,
    NodeRootFsInfo,
    VMListResponse,
    VMInfo,
    VMStatusResponse,
    VMMetricsResponse,
    VMMetricPoint,
)
from src.dependencies.proxmox import get_proxmox_client
from src.core.proxmox.client import ProxmoxClient
from src.core.response import SuccessResponse

proxmox_router = APIRouter(
    prefix="/proxmox",
    tags=["proxmox"],
)


# ==================== Cluster Resources API (권장) ====================

@proxmox_router.get("/cluster/resources/raw")
async def get_cluster_resources_raw(
    proxmox: ProxmoxClient = Depends(get_proxmox_client),
):
    """디버깅용: /cluster/resources raw 데이터 조회"""
    cluster_checker = proxmox.cluster()
    resources = await cluster_checker.get_all_resources()
    return {"resources": resources}


@proxmox_router.get("/cluster/nodes", response_model=SuccessResponse[ClusterNodesResponse])
async def get_cluster_nodes(
    proxmox: ProxmoxClient = Depends(get_proxmox_client),
):
    """클러스터의 모든 노드 상태 조회 (권장: /cluster/resources 사용)"""
    cluster_checker = proxmox.cluster()
    nodes_data = await cluster_checker.get_nodes()

    nodes = [
        ClusterNodeResource(
            node=n.get("node", ""),
            status=n.get("status", "unknown"),
            type=n.get("type", "node"),
            cpu=n.get("cpu"),
            maxcpu=n.get("maxcpu"),
            mem=n.get("mem"),
            maxmem=n.get("maxmem"),
            disk=n.get("disk"),
            maxdisk=n.get("maxdisk"),
            uptime=n.get("uptime"),
            level=n.get("level"),
        )
        for n in nodes_data
    ]

    return SuccessResponse(
        message="Cluster nodes retrieved successfully",
        data=ClusterNodesResponse(nodes=nodes),
    )


@proxmox_router.get("/cluster/vms", response_model=SuccessResponse[ClusterVMsResponse])
async def get_cluster_vms(
    node: Optional[str] = Query(default=None, description="특정 노드의 VM만 조회"),
    proxmox: ProxmoxClient = Depends(get_proxmox_client),
):
    """클러스터의 모든 VM 상태 조회 (권장: /cluster/resources 사용)"""
    cluster_checker = proxmox.cluster()
    vms_data = await cluster_checker.get_vms(node=node)

    vms = [
        ClusterVMResource(
            vmid=v.get("vmid", 0),
            node=v.get("node", ""),
            name=v.get("name"),
            status=v.get("status", "unknown"),
            type=v.get("type", "qemu"),
            cpu=v.get("cpu"),
            maxcpu=v.get("maxcpu"),
            mem=v.get("mem"),
            maxmem=v.get("maxmem"),
            disk=v.get("disk"),
            maxdisk=v.get("maxdisk"),
            uptime=v.get("uptime"),
            netin=v.get("netin"),
            netout=v.get("netout"),
            diskread=v.get("diskread"),
            diskwrite=v.get("diskwrite"),
            template=v.get("template"),
        )
        for v in vms_data
    ]

    return SuccessResponse(
        message="Cluster VMs retrieved successfully",
        data=ClusterVMsResponse(vms=vms, node=node),
    )


@proxmox_router.get("/cluster/nodes/{node_name}/storages", response_model=SuccessResponse[NodeStoragesResponse])
async def get_node_storages(
    node_name: str,
    proxmox: ProxmoxClient = Depends(get_proxmox_client),
):
    """특정 노드의 스토리지 상태 조회 (/nodes/{node}/storage)"""
    cluster_checker = proxmox.cluster()
    storages_data = await cluster_checker.get_storage(node=node_name)

    storages = [
        NodeStorageResource(
            storage=s.get("storage", ""),
            type=s.get("type", ""),
            content=s.get("content"),
            active=s.get("active"),
            enabled=s.get("enabled"),
            shared=s.get("shared"),
            total=s.get("total"),
            avail=s.get("avail"),
            used=s.get("used"),
            used_fraction=s.get("used_fraction"),
        )
        for s in storages_data
    ]

    return SuccessResponse(
        message="Node storages retrieved successfully",
        data=NodeStoragesResponse(node=node_name, storages=storages),
    )


# ==================== Legacy Node APIs ====================

@proxmox_router.get("/nodes", response_model=SuccessResponse[NodeListResponse])
async def list_nodes(
    proxmox: ProxmoxClient = Depends(get_proxmox_client),
):
    """Proxmox 클러스터의 모든 노드 목록 조회 (Legacy)"""
    node_checker = proxmox.node()
    nodes = await node_checker.list()

    return SuccessResponse(
        message="Nodes retrieved successfully",
        data=NodeListResponse(nodes=nodes),
    )


@proxmox_router.get("/nodes/{node_name}", response_model=SuccessResponse[NodeStatusResponse])
async def get_node_status(
    node_name: str,
    proxmox: ProxmoxClient = Depends(get_proxmox_client),
):
    """특정 노드의 상세 상태 조회 (Legacy)"""
    node_checker = proxmox.node()
    status = await node_checker.status(node_name)

    cpuinfo = None
    if "cpuinfo" in status:
        cpuinfo = NodeCpuInfo(
            cpus=status["cpuinfo"].get("cpus", 0),
            model=status["cpuinfo"].get("model"),
            mhz=status["cpuinfo"].get("mhz"),
            sockets=status["cpuinfo"].get("sockets"),
            cores=status["cpuinfo"].get("cores"),
            user_hz=status["cpuinfo"].get("user_hz"),
        )

    memory = None
    if "memory" in status:
        memory = NodeMemoryInfo(
            total=status["memory"].get("total", 0),
            used=status["memory"].get("used", 0),
            free=status["memory"].get("free", 0),
        )

    swap = None
    if "swap" in status:
        swap = NodeSwapInfo(
            total=status["swap"].get("total", 0),
            used=status["swap"].get("used", 0),
            free=status["swap"].get("free", 0),
        )

    rootfs = None
    if "rootfs" in status:
        rootfs = NodeRootFsInfo(
            total=status["rootfs"].get("total", 0),
            used=status["rootfs"].get("used", 0),
            free=status["rootfs"].get("free", 0),
            avail=status["rootfs"].get("avail", 0),
        )

    response = NodeStatusResponse(
        node=node_name,
        status="online",
        uptime=status.get("uptime"),
        cpu=status.get("cpu"),
        cpuinfo=cpuinfo,
        memory=memory,
        swap=swap,
        rootfs=rootfs,
        loadavg=status.get("loadavg"),
        kversion=status.get("kversion"),
        pveversion=status.get("pveversion"),
    )

    return SuccessResponse(
        message="Node status retrieved successfully",
        data=response,
    )


# ==================== Legacy VM APIs ====================

@proxmox_router.get("/nodes/{node_name}/vms", response_model=SuccessResponse[VMListResponse])
async def list_vms(
    node_name: str,
    proxmox: ProxmoxClient = Depends(get_proxmox_client),
):
    """특정 노드의 모든 VM 목록 조회 (Legacy)"""
    vm_checker = proxmox.vm()
    vmids = await vm_checker.list(node_name)

    vms = [VMInfo(vmid=vmid) for vmid in vmids]

    return SuccessResponse(
        message="VMs retrieved successfully",
        data=VMListResponse(node=node_name, vms=vms),
    )


@proxmox_router.get(
    "/nodes/{node_name}/vms/{vmid}",
    response_model=SuccessResponse[VMStatusResponse],
)
async def get_vm_status(
    node_name: str,
    vmid: int,
    proxmox: ProxmoxClient = Depends(get_proxmox_client),
):
    """특정 VM의 상세 상태 조회 (Legacy)"""
    vm_checker = proxmox.vm()
    status = await vm_checker.status(node_name, vmid)

    response = VMStatusResponse(
        vmid=vmid,
        name=status.get("name"),
        status=status.get("status", "unknown"),
        uptime=status.get("uptime"),
        cpu=status.get("cpu"),
        cpus=status.get("cpus"),
        mem=status.get("mem"),
        maxmem=status.get("maxmem"),
        disk=status.get("disk"),
        maxdisk=status.get("maxdisk"),
        netin=status.get("netin"),
        netout=status.get("netout"),
        diskread=status.get("diskread"),
        diskwrite=status.get("diskwrite"),
        pid=status.get("pid"),
        qmpstatus=status.get("qmpstatus"),
    )

    return SuccessResponse(
        message="VM status retrieved successfully",
        data=response,
    )


@proxmox_router.get(
    "/nodes/{node_name}/vms/{vmid}/metrics",
    response_model=SuccessResponse[VMMetricsResponse],
)
async def get_vm_metrics(
    node_name: str,
    vmid: int,
    timeframe: Literal["hour", "day", "week", "month", "year"] = Query(
        default="hour",
        description="메트릭 조회 기간 (hour, day, week, month, year)",
    ),
    proxmox: ProxmoxClient = Depends(get_proxmox_client),
):
    """특정 VM의 시계열 메트릭 조회"""
    vm_checker = proxmox.vm()
    metrics_data = await vm_checker.metrics(node_name, vmid, timeframe)

    data_points = []
    for point in metrics_data:
        data_points.append(
            VMMetricPoint(
                time=point.get("time", 0),
                cpu=point.get("cpu"),
                mem=point.get("mem"),
                maxmem=point.get("maxmem"),
                disk=point.get("disk"),
                maxdisk=point.get("maxdisk"),
                netin=point.get("netin"),
                netout=point.get("netout"),
                diskread=point.get("diskread"),
                diskwrite=point.get("diskwrite"),
            )
        )

    return SuccessResponse(
        message="VM metrics retrieved successfully",
        data=VMMetricsResponse(
            vmid=vmid,
            node=node_name,
            timeframe=timeframe,
            data=data_points,
        ),
    )
