# LimitRange Manager 가이드

## 개요

`LimitRangeManager`는 Kubernetes LimitRange 리소스를 관리하는 클래스입니다. LimitRange는 네임스페이스 내 개별 리소스의 기본 요청값과 허용 범위를 강제하여, 과도한 리소스 요청을 방지합니다.

## 주요 기능

### 1. LimitRange 생성 (`create_limitrange`)
- **멱등성 보장**: 동일한 이름의 LimitRange가 이미 존재하면 기존 리소스 반환
- **Container/Pod/PVC 타입** 제한 지원

```python
from kubernetes_asyncio.client import V1LimitRangeItem

manager = LimitRangeManager(k8s_client)

limits = [
    V1LimitRangeItem(
        type="Container",
        min={"cpu": "100m", "memory": "128Mi"},
        max={"cpu": "2", "memory": "2Gi"},
        default_request={"cpu": "200m", "memory": "256Mi"},
        default={"cpu": "500m", "memory": "512Mi"},
    ),
    V1LimitRangeItem(
        type="PersistentVolumeClaim",
        min={"storage": "1Gi"},
        max={"storage": "50Gi"},
    ),
]

limitrange = await manager.create_limitrange(
    name="project-limits",
    namespace="project-a",
    limits=limits,
)
```

### 2. LimitRange 조회 (`get_limitrange`)

```python
limitrange = await manager.get_limitrange(
    name="project-limits",
    namespace="project-a",
)
```

### 3. LimitRange 제한 업데이트 (`update_limits`)

```python
new_limits = [
    V1LimitRangeItem(
        type="Container",
        max={"cpu": "4", "memory": "4Gi"},
        default_request={"cpu": "300m", "memory": "512Mi"},
    )
]

limitrange = await manager.update_limits(
    name="project-limits",
    namespace="project-a",
    limits=new_limits,
)
```

### 4. LimitRange 삭제 (`delete_limitrange`)

```python
success = await manager.delete_limitrange(
    name="project-limits",
    namespace="project-a",
)
```

### 5. LimitRange 목록 조회 (`list_limitranges`)

```python
limitranges = await manager.list_limitranges(namespace="project-a")
```

### 6. 레이블 업데이트 (`update_labels`)

```python
limitrange = await manager.update_labels(
    name="project-limits",
    namespace="project-a",
    labels={"tier": "basic"},
    merge=True,
)
```

## 사용 사례

### 1. 프로젝트 기본 리소스 범위 강제
```python
await manager.create_limitrange(
    name="defaults",
    namespace="project-a",
    limits=[V1LimitRangeItem(type="Container", min={"cpu": "100m", "memory": "128Mi"})],
)
```

### 2. PVC 크기 범위 제한
```python
await manager.create_limitrange(
    name="storage-guardrail",
    namespace="project-a",
    limits=[V1LimitRangeItem(type="PersistentVolumeClaim", max={"storage": "50Gi"})],
)
```

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `LimitRangeCreationException` | LimitRange 생성 실패 |
| `LimitRangeReadException` | LimitRange 조회 실패 |
| `LimitRangeUpdateException` | LimitRange 업데이트 실패 |
| `LimitRangeDeletionException` | LimitRange 삭제 실패 |
| `LimitRangeListException` | LimitRange 목록 조회 실패 |

## 주의사항

1. **적용 시점**: LimitRange는 리소스 생성 시점에만 검증되며, 기존 리소스에는 영향 없음
2. **타입 구분**: Container/Pod/PVC 타입별로 제한이 다르게 적용됨
3. **기본값 주입**: defaultRequest/default는 요청값이 없는 리소스에 자동 적용

## 관련 리소스

- **ResourceQuota**: 네임스페이스 총량 제한
- **Namespace**: 격리 단위
- **PersistentVolumeClaim**: 스토리지 요청 대상
