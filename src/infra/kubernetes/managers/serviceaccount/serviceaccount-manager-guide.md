# ServiceAccount Manager 가이드

## 개요

`ServiceAccountManager`는 Kubernetes ServiceAccount 리소스를 관리하는 클래스입니다. ServiceAccount는 Pod가 Kubernetes API 또는 외부 시스템(Vault 등)에 접근할 때 사용하는 ID입니다.

## 주요 기능

### 1. ServiceAccount 생성 (`create_service_account`)
- **멱등성 보장**: 동일한 이름의 ServiceAccount가 이미 존재하면 기존 리소스 반환
- **ImagePullSecret 연결** 지원

```python
manager = ServiceAccountManager(k8s_client)

sa = await manager.create_service_account(
    name="app_deployment-sa",
    namespace="project-a",
    labels={"app_deployment": "myapp"},
    annotations={"owner": "platform-team"},
    image_pull_secrets=["registry-cred"],
)
```

### 2. ServiceAccount 조회 (`get_service_account`)

```python
sa = await manager.get_service_account(
    name="app_deployment-sa",
    namespace="project-a",
)
```

### 3. ServiceAccount 삭제 (`delete_service_account`)

```python
success = await manager.delete_service_account(
    name="app_deployment-sa",
    namespace="project-a",
)
```

### 4. ServiceAccount 목록 조회 (`list_service_accounts`)

```python
service_accounts = await manager.list_service_accounts(namespace="project-a")
```

### 5. 레이블 업데이트 (`update_labels`)

```python
sa = await manager.update_labels(
    name="app_deployment-sa",
    namespace="project-a",
    labels={"tier": "backend"},
    merge=True,
)
```

### 6. 어노테이션 업데이트 (`update_annotations`)

```python
sa = await manager.update_annotations(
    name="app_deployment-sa",
    namespace="project-a",
    annotations={"vault.hashicorp.com/role": "myapp-role"},
    merge=True,
)
```

### 7. ImagePullSecret 추가 (`add_image_pull_secret`)

```python
sa = await manager.add_image_pull_secret(
    name="app_deployment-sa",
    namespace="project-a",
    secret_name="registry-cred",
)
```

## 사용 사례

### 1. 이미지 레지스트리 인증 연결
```python
await manager.create_service_account(
    name="builder-sa",
    namespace="project-a",
    image_pull_secrets=["registry-cred"],
)
```

### 2. Vault 연동 어노테이션 설정
```python
await manager.update_annotations(
    name="app_deployment-sa",
    namespace="project-a",
    annotations={"vault.hashicorp.com/agent-inject": "true"},
)
```

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `ServiceAccountCreationException` | ServiceAccount 생성 실패 |
| `ServiceAccountReadException` | ServiceAccount 조회 실패 |
| `ServiceAccountUpdateException` | ServiceAccount 업데이트 실패 |
| `ServiceAccountDeletionException` | ServiceAccount 삭제 실패 |
| `ServiceAccountListException` | ServiceAccount 목록 조회 실패 |

## 주의사항

1. **권한 연계**: ServiceAccount는 RoleBinding을 통해 권한을 부여받음
2. **이미지 풀 시크릿**: 이미지 레지스트리 인증에 필요한 Secret을 연결 가능
3. **토큰 관리**: Kubernetes 버전에 따라 자동 토큰 생성 방식이 다를 수 있음

## 관련 리소스

- **Role/RoleBinding**: 권한 부여
- **Secret**: ImagePullSecret 및 토큰 저장소
