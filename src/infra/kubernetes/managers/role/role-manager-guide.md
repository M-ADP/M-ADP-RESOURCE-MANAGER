# Role Manager 가이드

## 개요

`RoleManager`는 Kubernetes Role 리소스를 관리하는 클래스입니다. Role은 네임스페이스 스코프의 RBAC 권한 집합을 정의합니다.

## 주요 기능

### 1. Role 생성 (`create_role`)
- **멱등성 보장**: 동일한 이름의 Role이 이미 존재하면 기존 리소스 반환
- **PolicyRule** 기반 권한 정의

```python
manager = RoleManager(k8s_client)

role = await manager.create_role(
    name="app-reader",
    namespace="project-a",
    rules=[
        {
            "apiGroups": [""],
            "resources": ["pods", "services"],
            "verbs": ["get", "list", "watch"],
        }
    ],
)
```

### 2. Role 조회 (`get_role`)

```python
role = await manager.get_role(
    name="app-reader",
    namespace="project-a",
)
```

### 3. Role 삭제 (`delete_role`)

```python
success = await manager.delete_role(
    name="app-reader",
    namespace="project-a",
)
```

### 4. Role 목록 조회 (`list_roles`)

```python
roles = await manager.list_roles(namespace="project-a")
```

### 5. 레이블 업데이트 (`update_labels`)

```python
role = await manager.update_labels(
    name="app-reader",
    namespace="project-a",
    labels={"scope": "readonly"},
    merge=True,
)
```

## 사용 사례

### 1. 앱 읽기 전용 권한
```python
await manager.create_role(
    name="app-readonly",
    namespace="project-a",
    rules=[{"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list"]}],
)
```

### 2. 로그 조회 권한
```python
await manager.create_role(
    name="pod-log-reader",
    namespace="project-a",
    rules=[{"apiGroups": [""], "resources": ["pods/log"], "verbs": ["get"]}],
)
```

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `RoleCreationException` | Role 생성 실패 |
| `RoleReadException` | Role 조회 실패 |
| `RoleUpdateException` | Role 업데이트 실패 |
| `RoleDeletionException` | Role 삭제 실패 |
| `RoleListException` | Role 목록 조회 실패 |

## 주의사항

1. **네임스페이스 스코프**: Role은 네임스페이스 범위에서만 적용
2. **정밀 권한**: 최소 권한 원칙을 지키는 정책 설계 필요
3. **RoleBinding 필요**: Role은 RoleBinding을 통해서만 실제 권한 부여

## 관련 리소스

- **RoleBinding**: Role과 주체를 연결
- **ServiceAccount**: 권한을 부여받는 주체
