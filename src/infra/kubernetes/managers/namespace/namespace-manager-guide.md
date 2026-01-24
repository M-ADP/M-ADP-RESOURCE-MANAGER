# Namespace Manager 가이드

## 개요

`NamespaceManager`는 Kubernetes Namespace 리소스를 관리하는 클래스입니다. Namespace는 클러스터 리소스를 논리적으로 분리하여 멀티 테넌시, 환경 분리, 리소스 할당을 관리합니다.

## 주요 기능

### 1. Namespace 생성 (`create_namespace`)
- **멱등성 보장**: 동일한 이름의 Namespace가 이미 존재하면 기존 리소스 반환
- **레이블 및 어노테이션 지원**

```python
manager = NamespaceManager(k8s_client)

# Namespace 생성
namespace = await manager.create_namespace(
    name="production",
    labels={"env": "prod", "team": "platform"},
    annotations={"owner": "platform-team"}
)
```

### 2. Namespace 조회 (`get_namespace`)

```python
namespace = await manager.get_namespace(name="production")
if namespace:
    print(f"Found namespace: {namespace.metadata.name}")
```

### 3. Namespace 삭제 (`delete_namespace`)
- **주의**: Namespace 내 모든 리소스가 함께 삭제됨
- 삭제 완료까지 시간이 걸릴 수 있음 (finalizer 처리)

```python
success = await manager.delete_namespace(name="production")
```

### 4. Namespace 목록 조회 (`list_namespaces`)

```python
# 전체 Namespace 조회
namespaces = await manager.list_namespaces()

# 레이블 셀렉터로 필터링
namespaces = await manager.list_namespaces(
    label_selector="env=prod"
)
```

### 5. 레이블 업데이트 (`update_labels`)

```python
namespace = await manager.update_labels(
    name="production",
    labels={"version": "v2"},
    merge=True
)
```

## 사용 사례

### 1. 환경별 분리
```python
# 개발, 스테이징, 프로덕션 환경 생성
await manager.create_namespace("development", labels={"env": "dev"})
await manager.create_namespace("staging", labels={"env": "staging"})
await manager.create_namespace("production", labels={"env": "prod"})
```

### 2. 팀별 분리
```python
await manager.create_namespace(
    "team-alpha",
    labels={"team": "alpha"},
    annotations={"contact": "alpha@example.com"}
)
```

### 3. 프로젝트별 분리
```python
await manager.create_namespace(
    "project-x",
    labels={"project": "x", "customer": "acme"},
    annotations={"budget": "high"}
)
```

## 멱등성 보장

- 동일한 이름의 Namespace 재생성 시 기존 리소스 반환

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `NamespaceCreationException` | Namespace 생성 실패 |
| `NamespaceReadException` | Namespace 조회 실패 |
| `NamespaceUpdateException` | Namespace 업데이트 실패 |
| `NamespaceDeletionException` | Namespace 삭제 실패 |
| `NamespaceListException` | Namespace 목록 조회 실패 |
| `NamespaceNotFoundException` | Namespace를 찾을 수 없음 |

## 주의사항

1. **예약된 이름**: `kube-system`, `kube-public`, `kube-node-lease`, `default`는 시스템 Namespace
2. **삭제 주의**: Namespace 삭제 시 내부 모든 리소스 삭제
3. **종료 대기**: Namespace 삭제는 비동기로 처리되며 완료까지 시간 소요
4. **네이밍 규칙**: DNS 호환 이름 (소문자, 숫자, 하이픈)
5. **리소스 쿼터**: ResourceQuota로 Namespace별 리소스 제한 가능

## 관련 리소스

- **ResourceQuota**: Namespace별 리소스 사용량 제한
- **LimitRange**: Namespace 내 리소스 기본값 및 제한
- **NetworkPolicy**: Namespace 간 네트워크 격리
- **ServiceAccount**: Namespace 스코프의 인증 주체
