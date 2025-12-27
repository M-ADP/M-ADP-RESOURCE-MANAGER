# RoleBinding Manager 가이드

## 개요

`RoleBindingManager`는 Kubernetes RoleBinding 리소스를 관리하는 클래스입니다. RoleBinding은 Role과 주체(ServiceAccount, User, Group)를 연결하여 권한을 부여합니다.

## 주요 기능

### 1. RoleBinding 생성 (`create_rolebinding`)
- **멱등성 보장**: 동일한 이름의 RoleBinding이 이미 존재하면 기존 리소스 반환

```python
manager = RoleBindingManager(k8s_client)

rolebinding = await manager.create_rolebinding(
    name="app-readonly-binding",
    namespace="project-a",
    role_name="app-reader",
    subjects=[
        {"kind": "ServiceAccount", "name": "app-sa", "namespace": "project-a"}
    ],
)
```

### 2. RoleBinding 조회 (`get_rolebinding`)

```python
rolebinding = await manager.get_rolebinding(
    name="app-readonly-binding",
    namespace="project-a",
)
```

### 3. RoleBinding 삭제 (`delete_rolebinding`)

```python
success = await manager.delete_rolebinding(
    name="app-readonly-binding",
    namespace="project-a",
)
```

### 4. RoleBinding 목록 조회 (`list_rolebindings`)

```python
rolebindings = await manager.list_rolebindings(namespace="project-a")
```

### 5. 레이블 업데이트 (`update_labels`)

```python
rolebinding = await manager.update_labels(
    name="app-readonly-binding",
    namespace="project-a",
    labels={"team": "platform"},
    merge=True,
)
```

### 6. Subject 추가 (`add_subject`)

```python
rolebinding = await manager.add_subject(
    name="app-readonly-binding",
    namespace="project-a",
    subject={"kind": "ServiceAccount", "name": "batch-sa", "namespace": "project-a"},
)
```

## 사용 사례

### 1. 앱 서비스 계정 권한 부여
```python
await manager.create_rolebinding(
    name="app-binding",
    namespace="project-a",
    role_name="app-reader",
    subjects=[{"kind": "ServiceAccount", "name": "app-sa", "namespace": "project-a"}],
)
```

### 2. 운영자 그룹 권한 부여
```python
await manager.create_rolebinding(
    name="ops-binding",
    namespace="project-a",
    role_name="admin-role",
    subjects=[{"kind": "Group", "name": "platform-ops", "apiGroup": "rbac.authorization.k8s.io"}],
)
```

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `RoleBindingCreationException` | RoleBinding 생성 실패 |
| `RoleBindingReadException` | RoleBinding 조회 실패 |
| `RoleBindingUpdateException` | RoleBinding 업데이트 실패 |
| `RoleBindingDeletionException` | RoleBinding 삭제 실패 |
| `RoleBindingListException` | RoleBinding 목록 조회 실패 |

## 주의사항

1. **Role 존재 필요**: RoleBinding은 대상 Role이 존재해야 생성 가능
2. **주체 범위**: Subject 종류에 따라 namespace/apiGroup 필요 여부가 다름
3. **권한 변경**: Role 변경 시 RoleBinding은 그대로 유지되므로 영향도 확인 필요

## 관련 리소스

- **Role**: 연결 대상 권한 집합
- **ServiceAccount**: 일반적인 주체
