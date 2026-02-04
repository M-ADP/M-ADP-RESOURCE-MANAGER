# ReplicaSet Manager 가이드

## 개요

`ReplicaSetManager`는 Kubernetes ReplicaSet 리소스를 관리하는 클래스입니다. ReplicaSet은 지정된 수의 Pod 레플리카를 항상 실행하도록 보장합니다.

## 주요 기능

### 1. ReplicaSet 생성 (`create_replicaset`)
- **멱등성 보장**: 동일한 이름의 ReplicaSet이 이미 존재하면 기존 리소스 반환
- **셀렉터 레이블 필수**: Pod 선택을 위한 레이블 필요

```python
from kubernetes_asyncio.client import V1Container

manager = ReplicaSetManager(k8s_client)

container = V1Container(
    name="app_deployment",
    image="nginx:1.21"
)

replicaset = await manager.create_replicaset(
    name="web-rs",
    namespace="production",
    containers=[container],
    replicas=3,
    labels={"app_deployment": "web", "version": "v1"}
)
```

### 2. ReplicaSet 조회 (`get_replicaset`)

```python
rs = await manager.get_replicaset(
    name="web-rs",
    namespace="production"
)
```

### 3. 레플리카 수 업데이트 (`update_replicas`)
- 동적 스케일링 지원

```python
rs = await manager.update_replicas(
    name="web-rs",
    namespace="production",
    replicas=5
)
```

### 4. ReplicaSet 상태 조회 (`get_replicaset_status`)

```python
status = await manager.get_replicaset_status(
    name="web-rs",
    namespace="production"
)

if status:
    print(f"Replicas: {status['replicas']}")
    print(f"Ready: {status['ready_replicas']}")
    print(f"Available: {status['available_replicas']}")
```

### 5. ReplicaSet 삭제 (`delete_replicaset`)

```python
success = await manager.delete_replicaset(
    name="web-rs",
    namespace="production"
)
```

## Deployment vs ReplicaSet

| 특징 | Deployment | ReplicaSet |
|------|-----------|-----------|
| 업데이트 전략 | 롤링 업데이트 지원 | 지원 안 함 |
| 롤백 | 이전 버전으로 롤백 가능 | 롤백 기능 없음 |
| 권장 사용 | 일반적인 워크로드 | 특수한 경우만 |
| 관리 수준 | 고수준 (ReplicaSet 자동 관리) | 저수준 |

**권장사항**: 대부분의 경우 Deployment 사용 권장. ReplicaSet은 Deployment가 내부적으로 관리.

## 멱등성 보장

- 동일한 이름의 ReplicaSet 재생성 시 기존 리소스 반환

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `ReplicaSetCreationException` | ReplicaSet 생성 실패 |
| `ReplicaSetReadException` | ReplicaSet 조회 실패 |
| `ReplicaSetUpdateException` | ReplicaSet 업데이트 실패 |
| `ReplicaSetDeletionException` | ReplicaSet 삭제 실패 |
| `ReplicaSetListException` | ReplicaSet 목록 조회 실패 |

## 주의사항

1. **Deployment 사용 권장**: 직접 ReplicaSet 생성보다 Deployment 사용
2. **셀렉터 불변성**: 생성 후 selector 수정 불가
3. **Pod 템플릿 변경**: 기존 Pod에 즉시 반영되지 않음 (삭제 후 재생성 필요)
4. **고아 Pod**: ReplicaSet 삭제 시 Pod도 함께 삭제됨

## 관련 리소스

- **Deployment**: ReplicaSet을 자동으로 생성/관리
- **Pod**: ReplicaSet이 생성/관리
- **HorizontalPodAutoscaler**: 자동 스케일링
