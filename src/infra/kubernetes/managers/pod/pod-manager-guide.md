# Pod Manager 가이드

## 개요

`PodManager`는 Kubernetes Pod 리소스를 관리하는 클래스입니다. 필요 시 Pod를 직접 생성/삭제할 수 있으며, 조회/모니터링 기능도 함께 제공합니다.

## 주요 기능

### 1. Pod 생성 (`create_pod`)

```python
from kubernetes_asyncio.client import V1Container

pod = await manager.create_pod(
    name="standalone-pod",
    namespace="project-a",
    containers=[V1Container(name="app_deployment", image="nginx:latest")],
    restart_policy="Always",
)
```

### 2. Pod 조회 (`get_pod`)

```python
manager = PodManager(k8s_client)

pod = await manager.get_pod(
    name="app_deployment-7c9b8f6d9f-abcde",
    namespace="project-a",
)
```

### 3. Pod 삭제 (`delete_pod`)

```python
success = await manager.delete_pod(
    name="standalone-pod",
    namespace="project-a",
)
```

### 4. Pod 목록 조회 (`list_pods`)

```python
pods = await manager.list_pods(
    namespace="project-a",
    label_selector="app_deployment=myapp",
)
```

### 5. Pod 상태 조회 (`get_pod_status`)

```python
status = await manager.get_pod_status(
    name="app_deployment-7c9b8f6d9f-abcde",
    namespace="project-a",
)
```

### 6. Pod 로그 조회 (`get_pod_logs`)

```python
logs = await manager.get_pod_logs(
    name="app_deployment-7c9b8f6d9f-abcde",
    namespace="project-a",
    container="app_deployment",
    tail_lines=200,
    timestamps=True,
)
```

### 7. 소유자 기준 Pod 조회 (`list_pods_by_owner`)

```python
pods = await manager.list_pods_by_owner(
    owner_name="myapp",
    owner_kind="Deployment",
    namespace="project-a",
)
```

## 사용 사례

### 1. 단일 Pod 실행
```python
await manager.create_pod(
    name="debug-pod",
    namespace="project-a",
    containers=[V1Container(name="debug", image="busybox")],
    restart_policy="Never",
)
```

### 2. 배포 상태 모니터링
```python
pods = await manager.list_pods(namespace="project-a", label_selector="app_deployment=myapp")
for pod in pods:
    status = await manager.get_pod_status(pod.metadata.name, pod.metadata.namespace)
    print(status["phase"])
```

### 3. 장애 원인 파악
```python
logs = await manager.get_pod_logs(
    name="myapp-xxxxx",
    namespace="project-a",
    tail_lines=100,
)
```

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `PodCreationException` | Pod 생성 실패 |
| `PodReadException` | Pod 조회/로그/상태 조회 실패 |
| `PodDeletionException` | Pod 삭제 실패 |
| `PodListException` | Pod 목록 조회 실패 |

## 주의사항

1. **권한 필요**: Pod 생성/삭제/로그 조회는 RBAC 권한 필요
2. **컨트롤러 우선**: 운영 환경에서는 Deployment/StatefulSet 권장
3. **상태 일관성**: Pod 상태는 짧은 간격으로 변동 가능

## 관련 리소스

- **Deployment/StatefulSet/DaemonSet**: Pod를 관리하는 상위 리소스
- **Service**: Pod 네트워크 엔드포인트
