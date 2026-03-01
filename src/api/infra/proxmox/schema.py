from typing import List, Optional
from pydantic import BaseModel


# ==================== Cluster Resource Schemas (권장) ====================

class ClusterNodeResource(BaseModel):
    """클러스터 노드 리소스 정보 (/cluster/resources?type=node)"""
    node: str
    status: str
    type: str = "node"
    cpu: Optional[float] = None
    maxcpu: Optional[int] = None
    mem: Optional[int] = None
    maxmem: Optional[int] = None
    disk: Optional[int] = None
    maxdisk: Optional[int] = None
    uptime: Optional[int] = None
    level: Optional[str] = None


class ClusterNodesResponse(BaseModel):
    """클러스터 노드 목록 응답"""
    nodes: List[ClusterNodeResource]


class ClusterVMResource(BaseModel):
    """클러스터 VM 리소스 정보 (qemu 또는 lxc)"""
    vmid: int
    node: str
    name: Optional[str] = None
    status: str
    type: str  # "qemu" 또는 "lxc"
    cpu: Optional[float] = None
    maxcpu: Optional[int] = None
    mem: Optional[int] = None
    maxmem: Optional[int] = None
    disk: Optional[int] = None
    maxdisk: Optional[int] = None
    uptime: Optional[int] = None
    netin: Optional[int] = None
    netout: Optional[int] = None
    diskread: Optional[int] = None
    diskwrite: Optional[int] = None
    template: Optional[int] = None


class ClusterVMsResponse(BaseModel):
    """클러스터 VM 목록 응답"""
    vms: List[ClusterVMResource]
    node: Optional[str] = None


class NodeStorageResource(BaseModel):
    """노드 스토리지 리소스 정보 (/nodes/{node}/storage)"""
    storage: str
    type: str  # rbd, dir, lvm, etc.
    content: Optional[str] = None
    active: Optional[int] = None
    enabled: Optional[int] = None
    shared: Optional[int] = None
    total: Optional[int] = None
    avail: Optional[int] = None
    used: Optional[int] = None
    used_fraction: Optional[float] = None


class NodeStoragesResponse(BaseModel):
    """노드 스토리지 목록 응답"""
    node: str
    storages: List[NodeStorageResource]


# ==================== Legacy Node Schemas ====================

class NodeListResponse(BaseModel):
    nodes: List[str]


class NodeCpuInfo(BaseModel):
    cpus: int
    model: Optional[str] = None
    mhz: Optional[str] = None
    sockets: Optional[int] = None
    cores: Optional[int] = None
    user_hz: Optional[int] = None


class NodeMemoryInfo(BaseModel):
    total: int
    used: int
    free: int


class NodeSwapInfo(BaseModel):
    total: int
    used: int
    free: int


class NodeRootFsInfo(BaseModel):
    total: int
    used: int
    free: int
    avail: int


class NodeStatusResponse(BaseModel):
    node: str
    status: str
    uptime: Optional[int] = None
    cpu: Optional[float] = None
    cpuinfo: Optional[NodeCpuInfo] = None
    memory: Optional[NodeMemoryInfo] = None
    swap: Optional[NodeSwapInfo] = None
    rootfs: Optional[NodeRootFsInfo] = None
    loadavg: Optional[List[str]] = None
    kversion: Optional[str] = None
    pveversion: Optional[str] = None


# ==================== Legacy VM Schemas ====================

class VMInfo(BaseModel):
    vmid: int
    name: Optional[str] = None
    status: Optional[str] = None


class VMListResponse(BaseModel):
    node: str
    vms: List[VMInfo]


class VMStatusResponse(BaseModel):
    vmid: int
    name: Optional[str] = None
    status: str
    uptime: Optional[int] = None
    cpu: Optional[float] = None
    cpus: Optional[int] = None
    mem: Optional[int] = None
    maxmem: Optional[int] = None
    disk: Optional[int] = None
    maxdisk: Optional[int] = None
    netin: Optional[int] = None
    netout: Optional[int] = None
    diskread: Optional[int] = None
    diskwrite: Optional[int] = None
    pid: Optional[int] = None
    qmpstatus: Optional[str] = None


class VMMetricPoint(BaseModel):
    time: int
    cpu: Optional[float] = None
    mem: Optional[float] = None
    maxmem: Optional[int] = None
    disk: Optional[int] = None
    maxdisk: Optional[int] = None
    netin: Optional[float] = None
    netout: Optional[float] = None
    diskread: Optional[float] = None
    diskwrite: Optional[float] = None


class VMMetricsResponse(BaseModel):
    vmid: int
    node: str
    timeframe: str
    data: List[VMMetricPoint]
