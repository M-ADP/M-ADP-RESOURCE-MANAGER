# Deployment Manager 가이드

## 개요

`DeploymentManager`는 Kubernetes Deployment 리소스를 관리하는 클래스입니다. Deployment는 애플리케이션의 선언적 업데이트를 제공하는 워크로드 리소스로, Pod와 ReplicaSet을 관리합니다.

## 주요 기능

### 1. Deployment 생성 (`create_deployment`)
- **멱등성 보장**: 동일한 이름의 Deployment가 이미 존재하면 기존 리소스 반환
- **기본 레이블 자동 설정**: labels 미제공 시 `{"app": name}` 자동 설정
- **컨테이너 설정**: 하나 이상의 컨테이너 정의 필요
- **레플리카 수 설정**: 기본값 1개

```python
from kubernetes_asyncio.client import V1Container

manager = DeploymentManager(k8s_client)

# 컨테이너 정의
container = V1Container(
    name="nginx",
    image="nginx:1.21",
    ports=[V1ContainerPort(container_port=80)]
)

# Deployment 생성
deployment = await manager.create_deployment(
    name="my-app",
    namespace="production",
    containers=[container],
    replicas=3,
    labels={"app": "my-app", "env": "prod"}
)
```

### 2. Deployment 조회 (`get_deployment`)
- 특정 Deployment 조회
- 존재하지 않으면 `None` 반환

```python
deployment = await manager.get_deployment(
    name="my-app",
    namespace="production"
)

if deployment:
    print(f"Found deployment: {deployment.metadata.name}")
```

### 3. Deployment 삭제 (`delete_deployment`)
- **유예 기간 설정 가능**: `grace_period_seconds` 지정
- 존재하지 않는 리소스 삭제 시 예외 발생

```python
success = await manager.delete_deployment(
    name="my-app",
    namespace="production",
    grace_period_seconds=30
)
```

### 4. Deployment 목록 조회 (`list_deployments`)
- 네임스페이스별 또는 전체 조회
- 레이블/필드 셀렉터 지원

```python
# 특정 네임스페이스의 모든 Deployment
deployments = await manager.list_deployments(
    namespace="production"
)

# 레이블 셀렉터로 필터링
deployments = await manager.list_deployments(
    namespace="production",
    label_selector="app=my-app,env=prod"
)
```

### 5. 레플리카 수 업데이트 (`update_replicas`)
- 동적 스케일링 지원
- Patch 방식으로 업데이트

```python
deployment = await manager.update_replicas(
    name="my-app",
    namespace="production",
    replicas=5
)
```

### 6. 레이블 업데이트 (`update_labels`)
- **병합 모드**: 기존 레이블 유지하며 새 레이블 추가
- **교체 모드**: 모든 레이블 교체

```python
# 병합 모드 (기본)
deployment = await manager.update_labels(
    name="my-app",
    namespace="production",
    labels={"version": "v2.0"},
    merge=True
)

# 교체 모드
deployment = await manager.update_labels(
    name="my-app",
    namespace="production",
    labels={"app": "my-app-v2"},
    merge=False
)
```

### 7. Deployment 상태 조회 (`get_deployment_status`)
- replicas, ready_replicas, available_replicas 등 확인
- conditions를 통한 상태 진단

```python
status = await manager.get_deployment_status(
    name="my-app",
    namespace="production"
)

if status:
    print(f"Available: {status['available_replicas']}/{status['replicas']}")
    for condition in status['conditions']:
        print(f"{condition['type']}: {condition['status']}")
```

### 8. 존재 여부 확인 (`exists`)

```python
if await manager.exists("my-app", "production"):
    print("Deployment exists")
```

## 멱등성 보장

모든 생성 작업은 멱등성을 보장합니다:
- 동일한 요청을 여러 번 호출해도 결과는 동일
- 409 Conflict 발생 시 자동 재조회

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `DeploymentCreationException` | Deployment 생성 실패 |
| `DeploymentReadException` | Deployment 조회 실패 (404 제외) |
| `DeploymentUpdateException` | Deployment 업데이트 실패 |
| `DeploymentDeletionException` | Deployment 삭제 실패 |
| `DeploymentListException` | Deployment 목록 조회 실패 |

## 주의사항

1. **컨테이너 필수**: 최소 1개 이상의 컨테이너 정의 필요
2. **네임스페이스 사전 생성**: 대상 네임스페이스가 미리 존재해야 함
3. **셀렉터 일치**: selector_labels와 pod_labels는 일치해야 함
4. **리소스 한계**: 컨테이너 리소스 requests/limits 설정 권장

## 관련 리소스

- **ReplicaSet**: Deployment가 자동으로 생성/관리
- **Pod**: ReplicaSet이 생성/관리
- **Service**: Deployment의 Pod를 외부에 노출
- **HorizontalPodAutoscaler**: Deployment의 자동 스케일링
