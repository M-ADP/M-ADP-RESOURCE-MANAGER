# ResourceQuota Manager 가이드

## 개요

`ResourceQuotaManager`는 Kubernetes ResourceQuota 리소스를 관리하는 클래스입니다. ResourceQuota는 네임스페이스 전체의 리소스 사용량 총합을 제한합니다.

## 주요 기능

### 1. ResourceQuota 생성 (`create_resource_quota`)
- **멱등성 보장**: 동일한 이름의 ResourceQuota가 이미 존재하면 기존 리소스 반환
- **컴퓨팅/스토리지/오브젝트 개수 제한** 지원

```python
manager = ResourceQuotaManager(k8s_client)

quota = await manager.create_resource_quota(
    name="project-quota",
    namespace="project-a",
    hard_limits={
        "requests.cpu": "4",
        "limits.cpu": "8",
        "requests.memory": "8Gi",
        "limits.memory": "16Gi",
        "requests.storage": "100Gi",
        "pods": "50",
        "services": "10",
        "persistentvolumeclaims": "20",
    },
)
```

### 2. ResourceQuota 조회 (`get_resource_quota`)

```python
quota = await manager.get_resource_quota(
    name="project-quota",
    namespace="project-a",
)
```

### 3. ResourceQuota 업데이트 (`update_resource_quota`)

```python
quota = await manager.update_resource_quota(
    name="project-quota",
    namespace="project-a",
    hard_limits={
        "requests.cpu": "6",
        "requests.memory": "12Gi",
        "pods": "80",
    },
)
```

### 4. ResourceQuota 상태 조회 (`get_quota_status`)

```python
status = await manager.get_quota_status(
    name="project-quota",
    namespace="project-a",
)
```

### 5. ResourceQuota 삭제 (`delete_resource_quota`)

```python
success = await manager.delete_resource_quota(
    name="project-quota",
    namespace="project-a",
)
```

### 6. ResourceQuota 목록 조회 (`list_resource_quotas`)

```python
quotas = await manager.list_resource_quotas(namespace="project-a")
```

### 7. 레이블 업데이트 (`update_labels`)

```python
quota = await manager.update_labels(
    name="project-quota",
    namespace="project-a",
    labels={"tier": "standard"},
    merge=True,
)
```

## 사용 사례

### 1. 프로젝트 총량 상한 적용
```python
await manager.create_resource_quota(
    name="defaults",
    namespace="project-a",
    hard_limits={"requests.cpu": "4", "requests.memory": "8Gi"},
)
```

### 2. 오브젝트 개수 제한
```python
await manager.create_resource_quota(
    name="object-guardrail",
    namespace="project-a",
    hard_limits={"pods": "50", "services": "10"},
)
```

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `ResourceQuotaCreationException` | ResourceQuota 생성 실패 |
| `ResourceQuotaReadException` | ResourceQuota 조회 실패 |
| `ResourceQuotaUpdateException` | ResourceQuota 업데이트 실패 |
| `ResourceQuotaDeletionException` | ResourceQuota 삭제 실패 |
| `ResourceQuotaListException` | ResourceQuota 목록 조회 실패 |

## 주의사항

1. **총량 제한**: ResourceQuota는 네임스페이스 전체 합계를 제한
2. **적용 시점**: 리소스 생성/확장 시점에 quota가 검증됨
3. **범위 지정**: scopes/scopeSelector로 특정 우선순위 등에만 적용 가능

## 관련 리소스

- **LimitRange**: 개별 리소스의 기본값/범위 제한
- **Namespace**: 격리 단위
- **PersistentVolumeClaim**: 스토리지 사용량 집계 대상
