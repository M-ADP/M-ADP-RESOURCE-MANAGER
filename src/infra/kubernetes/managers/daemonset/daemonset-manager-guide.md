# DaemonSet Manager 가이드

## 개요

DaemonSet Manager는 **모든 (또는 특정) 노드에 Pod를 자동으로 배포**하는 Kubernetes DaemonSet 리소스를 관리합니다.

DaemonSet의 핵심 특징:
- **노드당 정확히 하나의 Pod**: 각 노드에 자동으로 Pod가 배포됨
- **노드 추가/제거 시 자동 반응**: 새 노드가 추가되면 자동으로 Pod 생성
- **노드 셀렉터 지원**: 특정 노드에만 배포 가능
- **시스템 레벨 작업에 적합**: 로깅, 모니터링, 네트워크 플러그인 등

대표적인 사용 사례:
- **로그 수집기**: Fluentd, Filebeat, Logstash
- **모니터링 에이전트**: Prometheus Node Exporter, Datadog Agent
- **네트워크 플러그인**: Calico, Weave
- **스토리지 데몬**: GlusterFS, Ceph
- **보안 에이전트**: 취약점 스캐너, 침입 탐지 시스템

---

## 주요 기능

### 1. DaemonSet 생성 (멱등성 보장)

```python
from kubernetes_asyncio.client import V1Container

# 기본 DaemonSet 생성
daemonset = await manager.create_daemonset(
    name="node-exporter",
    namespace="monitoring",
    containers=[
        V1Container(
            name="node-exporter",
            image="prom/node-exporter:latest",
            ports=[{"containerPort": 9100, "name": "metrics"}],
            args=["--path.procfs=/host/proc", "--path.sysfs=/host/sys"],
            volume_mounts=[
                {"name": "proc", "mountPath": "/host/proc", "readOnly": True},
                {"name": "sys", "mountPath": "/host/sys", "readOnly": True}
            ]
        )
    ],
    labels={"app": "node-exporter", "tier": "monitoring"},
    annotations={"prometheus.io/scrape": "true"}
)

print(f"DaemonSet 생성됨: {daemonset.metadata.name}")
```

### 2. 레이블 커스터마이징

```python
# Pod와 DaemonSet에 서로 다른 레이블 적용
daemonset = await manager.create_daemonset(
    name="fluentd",
    namespace="logging",
    containers=[...],
    labels={"app": "fluentd", "component": "logging"},  # DaemonSet 레이블
    selector_labels={"app": "fluentd"},  # Pod 선택 레이블
    pod_labels={"app": "fluentd", "version": "v2"},  # Pod 레이블
    pod_annotations={"sidecar.istio.io/inject": "false"}  # Pod 어노테이션
)
```

### 3. DaemonSet 조회

```python
# 단일 DaemonSet 조회
ds = await manager.get_daemonset("node-exporter", "monitoring")
if ds:
    print(f"DaemonSet 발견: {ds.metadata.name}")
    print(f"Desired: {ds.status.desired_number_scheduled}")
    print(f"Ready: {ds.status.number_ready}")
else:
    print("DaemonSet이 존재하지 않음")

# 존재 여부 확인
exists = await manager.exists("node-exporter", "monitoring")
```

### 4. DaemonSet 목록 조회

```python
# 특정 네임스페이스의 모든 DaemonSet
daemonsets = await manager.list_daemonsets(namespace="kube-system")

# 레이블 셀렉터로 필터링
monitoring_ds = await manager.list_daemonsets(
    namespace="monitoring",
    label_selector="tier=monitoring"
)

# 전체 클러스터의 DaemonSet
all_daemonsets = await manager.list_daemonsets()
```

### 5. DaemonSet 상태 조회

```python
status = await manager.get_daemonset_status("node-exporter", "monitoring")
if status:
    print(f"Desired Nodes: {status['desired_number_scheduled']}")
    print(f"Current Scheduled: {status['current_number_scheduled']}")
    print(f"Ready: {status['number_ready']}")
    print(f"Available: {status['number_available']}")
    print(f"Misscheduled: {status['number_misscheduled']}")
    print(f"Updated: {status['updated_number_scheduled']}")
    
    # Conditions 확인
    for condition in status['conditions']:
        print(f"{condition['type']}: {condition['status']} - {condition['message']}")
```

### 6. 레이블 업데이트

```python
# 레이블 추가/병합
updated = await manager.update_labels(
    name="node-exporter",
    namespace="monitoring",
    labels={"version": "v1.5", "environment": "production"},
    merge=True  # 기존 레이블과 병합
)

print(f"업데이트된 레이블: {updated.metadata.labels}")
```

### 7. DaemonSet 삭제

```python
# DaemonSet 삭제 (모든 노드의 Pod도 함께 삭제됨)
success = await manager.delete_daemonset(
    name="node-exporter",
    namespace="monitoring",
    grace_period_seconds=30
)

if success:
    print("DaemonSet 및 모든 Pod 삭제 완료")
```

---

## 사용 시나리오

### 시나리오 1: Prometheus Node Exporter 배포

```python
# 모든 노드에서 시스템 메트릭 수집
node_exporter = await manager.create_daemonset(
    name="node-exporter",
    namespace="monitoring",
    containers=[
        V1Container(
            name="node-exporter",
            image="prom/node-exporter:v1.5.0",
            ports=[{"containerPort": 9100, "name": "metrics"}],
            args=[
                "--path.procfs=/host/proc",
                "--path.sysfs=/host/sys",
                "--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)"
            ],
            volume_mounts=[
                {"name": "proc", "mountPath": "/host/proc", "readOnly": True},
                {"name": "sys", "mountPath": "/host/sys", "readOnly": True},
                {"name": "root", "mountPath": "/rootfs", "readOnly": True}
            ]
        )
    ],
    labels={"app": "node-exporter"},
    pod_annotations={
        "prometheus.io/scrape": "true",
        "prometheus.io/port": "9100"
    }
)

# 모든 노드에 배포될 때까지 대기
while True:
    status = await manager.get_daemonset_status("node-exporter", "monitoring")
    if (status['number_ready'] == status['desired_number_scheduled']):
        print(f"Node Exporter가 {status['number_ready']}개 노드에 배포 완료")
        break
    await asyncio.sleep(5)
```

### 시나리오 2: Fluentd 로그 수집기 배포

```python
# 모든 노드의 로그를 수집하여 중앙 집중화
fluentd = await manager.create_daemonset(
    name="fluentd",
    namespace="logging",
    containers=[
        V1Container(
            name="fluentd",
            image="fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch",
            env=[
                {"name": "FLUENT_ELASTICSEARCH_HOST", "value": "elasticsearch.logging.svc"},
                {"name": "FLUENT_ELASTICSEARCH_PORT", "value": "9200"}
            ],
            resources={
                "limits": {"memory": "512Mi", "cpu": "500m"},
                "requests": {"memory": "256Mi", "cpu": "200m"}
            },
            volume_mounts=[
                {"name": "varlog", "mountPath": "/var/log"},
                {"name": "varlibdockercontainers", "mountPath": "/var/lib/docker/containers", "readOnly": True}
            ]
        )
    ],
    labels={"app": "fluentd", "component": "logging"}
)
```

### 시나리오 3: 특정 노드에만 배포 (Node Selector)

```python
# GPU 노드에만 GPU 모니터링 에이전트 배포
# (nodeSelector는 PodSpec에 포함되므로 containers 생성 시 함께 설정)

from kubernetes_asyncio.client import V1PodSpec, V1PodTemplateSpec

gpu_monitor = await manager.create_daemonset(
    name="gpu-monitor",
    namespace="monitoring",
    containers=[
        V1Container(
            name="nvidia-gpu-exporter",
            image="nvidia/dcgm-exporter:latest",
            ports=[{"containerPort": 9400}]
        )
    ],
    labels={"app": "gpu-monitor"}
)

# Note: nodeSelector는 K8s API를 직접 사용하여 spec.template.spec.nodeSelector에 설정
# 예: {"accelerator": "nvidia-tesla-p100"}
```

### 시나리오 4: Rolling Update 모니터링

```python
# DaemonSet 이미지 업데이트 후 배포 상태 모니터링
# (이미지 업데이트는 kubectl apply 또는 직접 API 호출로 수행)

print("Rolling Update 진행 상황 모니터링...")
while True:
    status = await manager.get_daemonset_status("fluentd", "logging")
    
    total = status['desired_number_scheduled']
    updated = status['updated_number_scheduled']
    ready = status['number_ready']
    
    print(f"진행: {updated}/{total} 업데이트됨, {ready}/{total} 준비됨")
    
    # 모든 Pod가 업데이트되고 준비되면 완료
    if updated == total and ready == total:
        print("Rolling Update 완료!")
        break
    
    await asyncio.sleep(10)
```

---

## 모범 사례

### 1. 리소스 제한 설정

DaemonSet은 모든 노드에서 실행되므로 **반드시 리소스 제한을 설정**해야 합니다:

```python
containers=[
    V1Container(
        name="fluentd",
        image="fluent/fluentd:latest",
        resources={
            "limits": {
                "memory": "512Mi",  # 최대 메모리
                "cpu": "500m"       # 최대 CPU (0.5 core)
            },
            "requests": {
                "memory": "256Mi",  # 보장 메모리
                "cpu": "200m"       # 보장 CPU (0.2 core)
            }
        }
    )
]
```

### 2. HostPath 볼륨 사용

노드의 파일시스템에 접근할 때 HostPath 볼륨 사용:

```python
# 주의: HostPath는 보안 위험이 있으므로 읽기 전용 권장

volume_mounts=[
    {"name": "varlog", "mountPath": "/var/log", "readOnly": True},
    {"name": "containers", "mountPath": "/var/lib/docker/containers", "readOnly": True}
]

# volumes 설정은 PodSpec에 포함
# volumes=[
#     {"name": "varlog", "hostPath": {"path": "/var/log"}},
#     {"name": "containers", "hostPath": {"path": "/var/lib/docker/containers"}}
# ]
```

### 3. Tolerations 설정

마스터 노드 포함 모든 노드에 배포하려면 Toleration 필요:

```python
# master/control-plane 노드에도 배포
# (Toleration은 PodSpec에 포함)

# tolerations=[
#     {
#         "key": "node-role.kubernetes.io/master",
#         "operator": "Exists",
#         "effect": "NoSchedule"
#     },
#     {
#         "key": "node-role.kubernetes.io/control-plane",
#         "operator": "Exists",
#         "effect": "NoSchedule"
#     }
# ]
```

### 4. DaemonSet vs Deployment

| 기준 | DaemonSet | Deployment |
|------|-----------|------------|
| Pod 배포 전략 | 노드당 1개 | 지정된 replica 수 |
| 노드 선택 | 모든 노드 (또는 nodeSelector) | 스케줄러가 자동 선택 |
| 스케일링 | 불가능 (노드 수에 따름) | 수동/자동 스케일링 가능 |
| 사용 사례 | 시스템 데몬, 모니터링 | 애플리케이션 워크로드 |
| 노드 추가 시 | 자동으로 Pod 생성 | 변화 없음 |

---

## 예외 처리

| 예외 클래스 | 발생 시점 | 처리 방법 |
|-----------|---------|---------|
| `DaemonSetCreationException` | DaemonSet 생성 실패 | 레이블 셀렉터 확인, RBAC 권한 확인 |
| `DaemonSetReadException` | DaemonSet 조회 실패 (404 제외) | 네임스페이스 확인, API 서버 상태 확인 |
| `DaemonSetUpdateException` | DaemonSet 업데이트 실패 | Spec 유효성 확인, 레이블 불변성 확인 |
| `DaemonSetDeletionException` | DaemonSet 삭제 실패 | Finalizer 확인, Pod 종료 대기 |
| `DaemonSetListException` | 목록 조회 실패 | RBAC 권한 확인, 네트워크 상태 확인 |

```python
from src.infra.kubernetes.managers.daemonset.exceptions import (
    DaemonSetCreationException,
    DaemonSetDeletionException
)

try:
    ds = await manager.create_daemonset(
        name="node-exporter",
        namespace="monitoring",
        containers=[...]
    )
except DaemonSetCreationException as e:
    print(f"DaemonSet 생성 실패: {e.reason}")
    print(f"상세 정보: {e.detail}")
```

---

## 주의사항

### 1. 모든 노드에 Pod 생성됨

```python
# ⚠️ DaemonSet은 조건에 맞는 모든 노드에 Pod를 생성
# 100개 노드 클러스터 → 100개 Pod 생성

ds = await manager.create_daemonset(
    name="heavy-app",
    namespace="default",
    containers=[...]  # 리소스가 많이 필요한 컨테이너
)
# → 노드 리소스 부족 위험!
```

### 2. 삭제 시 존재하지 않으면 예외 발생

```python
# ❌ DaemonSet이 없으면 예외 발생
try:
    await manager.delete_daemonset("non-existent", "default")
except DaemonSetDeletionException:
    print("DaemonSet이 존재하지 않아 삭제 실패")

# ✅ 존재 여부 먼저 확인
if await manager.exists("node-exporter", "monitoring"):
    await manager.delete_daemonset("node-exporter", "monitoring")
```

### 3. 레이블 셀렉터는 불변

```python
# ⚠️ DaemonSet 생성 후 selector는 변경할 수 없음
# selector를 변경하려면 DaemonSet을 삭제하고 재생성해야 함

ds = await manager.create_daemonset(
    name="app",
    namespace="default",
    selector_labels={"app": "myapp"},  # 이 값은 불변
    containers=[...]
)

# selector 변경 불가능!
```

---

## 관련 리소스

- **ConfigMap Manager**: 설정 데이터를 DaemonSet Pod에 주입
- **Secret Manager**: 민감한 데이터 관리
- **Service Manager**: DaemonSet Pod에 대한 서비스 노출

---

## 참고

- DaemonSet은 **모든 노드**에 시스템 레벨 서비스를 배포할 때 사용합니다
- **Deployment**는 일반 애플리케이션 워크로드에 사용하세요
- RMS 원칙에 따라 **멱등성이 보장**됩니다
- 모든 작업은 **비동기(async/await)** 로 수행됩니다
- 노드 수가 변경되면 **자동으로 Pod가 생성/삭제**됩니다
