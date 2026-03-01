# PersistentVolumeClaim Manager 가이드

## 개요

`PersistentVolumeClaimManager`는 Kubernetes PersistentVolumeClaim (PVC) 리소스를 관리하는 클래스입니다. PVC는 애플리케이션이 영구 스토리지를 요청하는 리소스로, PersistentVolume (PV)에 바인딩되어 데이터를 영구적으로 저장합니다.

## 주요 기능

### 1. PVC 생성 (`create_pvc`)
- **멱등성 보장**: 동일한 이름의 PVC가 이미 존재하면 기존 리소스 반환
- **스토리지 크기 지정**: 필수 파라미터
- **접근 모드 설정**: ReadWriteOnce (기본), ReadOnlyMany, ReadWriteMany
- **스토리지 클래스 선택**: 동적 프로비저닝 지원

```python
manager = PersistentVolumeClaimManager(k8s_client)

# PVC 생성
pvc = await manager.create_pvc(
    name="app_deployment-data",
    namespace="production",
    storage_size="10Gi",
    access_modes=["ReadWriteOnce"],
    storage_class_name="fast-ssd",
    labels={"app_deployment": "myapp", "tier": "data"}
)
```

### 2. 접근 모드 (Access Modes)

| 모드 | 설명 | 약어 |
|------|------|------|
| ReadWriteOnce | 단일 노드에서 읽기-쓰기 | RWO |
| ReadOnlyMany | 여러 노드에서 읽기 전용 | ROX |
| ReadWriteMany | 여러 노드에서 읽기-쓰기 | RWX |

```python
# 여러 노드에서 읽기-쓰기 가능한 PVC
pvc = await manager.create_pvc(
    name="shared-data",
    namespace="production",
    storage_size="50Gi",
    access_modes=["ReadWriteMany"],
    storage_class_name="nfs"
)
```

### 3. PVC 조회 (`get_pvc`)

```python
pvc = await manager.get_pvc(
    name="app_deployment-data",
    namespace="production"
)

if pvc:
    print(f"Storage: {pvc.spec.resources.requests['storage']}")
    print(f"Access Modes: {pvc.spec.access_modes}")
```

### 4. PVC 삭제 (`delete_pvc`)
- **주의**: PVC 삭제 시 바인딩된 PV의 데이터도 삭제될 수 있음 (ReclaimPolicy에 따라)

```python
success = await manager.delete_pvc(
    name="app_deployment-data",
    namespace="production",
    grace_period_seconds=30
)
```

### 5. PVC 크기 변경 (`resize_pvc`)
- **증가만 가능**: 스토리지 크기 축소 불가
- **StorageClass 요구사항**: `allowVolumeExpansion: true` 필요
- **온라인 확장**: 대부분의 스토리지 클래스에서 Pod 재시작 없이 확장 가능

```python
pvc = await manager.resize_pvc(
    name="app_deployment-data",
    namespace="production",
    new_storage_size="20Gi"  # 10Gi -> 20Gi로 확장
)
```

### 6. PVC 상태 조회 (`get_pvc_status`)

```python
status = await manager.get_pvc_status(
    name="app_deployment-data",
    namespace="production"
)

if status:
    print(f"Phase: {status['phase']}")  # Bound, Pending, Lost
    print(f"Capacity: {status['capacity']}")
    print(f"Access Modes: {status['access_modes']}")
```

### 7. PVC 바인딩 확인 (`is_bound`)

```python
if await manager.is_bound("app_deployment-data", "production"):
    print("PVC is bound to a PV")
else:
    print("PVC is pending or lost")
```

### 8. PVC 목록 조회 (`list_pvcs`)

```python
# 네임스페이스별 조회
pvcs = await manager.list_pvcs(namespace="production")

# 레이블 셀렉터로 필터링
pvcs = await manager.list_pvcs(
    namespace="production",
    label_selector="app_deployment=myapp"
)
```

## PVC 라이프사이클

### 1. Pending
- PVC가 생성되었지만 PV에 바인딩되지 않음
- 적합한 PV를 찾는 중 또는 동적 프로비저닝 대기 중

### 2. Bound
- PVC가 PV에 성공적으로 바인딩됨
- 애플리케이션에서 사용 가능

### 3. Lost
- 바인딩된 PV가 삭제되었지만 PVC는 남아있음
- 데이터 복구 불가

## 스토리지 클래스 활용

### 동적 프로비저닝
```python
# StorageClass가 자동으로 PV 생성
pvc = await manager.create_pvc(
    name="dynamic-storage",
    namespace="default",
    storage_size="5Gi",
    storage_class_name="standard"  # 사전 정의된 StorageClass
)
```

### 정적 프로비저닝
```python
from kubernetes_asyncio.client import V1LabelSelector

# 특정 PV 선택
pvc = await manager.create_pvc(
    name="static-storage",
    namespace="default",
    storage_size="10Gi",
    selector=V1LabelSelector(
        match_labels={"disk": "ssd"}
    )
)
```

## 예제 시나리오

### 1. 데이터베이스 스토리지
```python
# 고성능 SSD 스토리지
pvc = await manager.create_pvc(
    name="postgres-data",
    namespace="databases",
    storage_size="100Gi",
    access_modes=["ReadWriteOnce"],
    storage_class_name="fast-ssd"
)
```

### 2. 공유 파일 스토리지
```python
# 여러 Pod에서 공유
pvc = await manager.create_pvc(
    name="shared-files",
    namespace="apps",
    storage_size="50Gi",
    access_modes=["ReadWriteMany"],
    storage_class_name="nfs"
)
```

### 3. 로그 수집 스토리지
```python
# 로그 수집용 대용량 스토리지
pvc = await manager.create_pvc(
    name="log-storage",
    namespace="logging",
    storage_size="500Gi",
    access_modes=["ReadWriteOnce"],
    storage_class_name="standard"
)
```

## 멱등성 보장

- 동일한 이름의 PVC 재생성 시 기존 PVC 반환
- 409 Conflict 발생 시 자동 재조회

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `PersistentVolumeClaimCreationException` | PVC 생성 실패 |
| `PersistentVolumeClaimReadException` | PVC 조회 실패 (404 제외) |
| `PersistentVolumeClaimUpdateException` | PVC 업데이트 실패 |
| `PersistentVolumeClaimDeletionException` | PVC 삭제 실패 |
| `PersistentVolumeClaimListException` | PVC 목록 조회 실패 |

## 주의사항

1. **스토리지 크기**: 축소 불가, 증가만 가능
2. **접근 모드 제한**: 스토리지 백엔드에 따라 지원되는 모드 다름
3. **삭제 정책**: PV의 ReclaimPolicy 확인 필요 (Delete, Retain, Recycle)
4. **네임스페이스 스코프**: PVC는 네임스페이스 리소스
5. **바인딩 대기**: Pending 상태에서 장시간 대기 시 PV/StorageClass 확인
6. **볼륨 확장**: StorageClass의 `allowVolumeExpansion` 설정 필요
7. **사용 중 삭제 방지**: Pod에 마운트된 PVC는 삭제 불가

## 관련 리소스

- **PersistentVolume (PV)**: PVC가 바인딩되는 실제 스토리지
- **StorageClass**: 동적 프로비저닝을 위한 스토리지 템플릿
- **Pod/Deployment**: PVC를 볼륨으로 마운트
- **StatefulSet**: 각 Pod마다 고유한 PVC 자동 생성
