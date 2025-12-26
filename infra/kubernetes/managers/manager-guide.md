# Kubernetes Resource Manager 가이드

M-ADP Resource Manager Server의 Kubernetes 리소스 관리 계층 가이드입니다.

## 목차
- [개요](#개요)
- [공통 특징](#공통-특징)
- [Manager 목록](#manager-목록)
  - [NamespaceManager](#namespacemanager)
  - [ServiceAccountManager](#serviceaccountmanager)
  - [RoleManager](#rolemanager)
  - [RoleBindingManager](#rolebindingmanager)
  - [ConfigMapManager](#configmapmanager)
  - [SecretManager](#secretmanager)
  - [DeploymentManager](#deploymentmanager)
  - [StatefulSetManager](#statefulsetmanager)
  - [ServiceManager](#servicemanager)
  - [PodManager](#podmanager)
- [사용 패턴](#사용-패턴)
- [예외 처리](#예외-처리)
- [테스트](#테스트)

---

## 개요

각 Manager는 특정 Kubernetes 리소스의 생성, 조회, 수정, 삭제를 담당하는 **비동기 클래스**입니다. 모든 Manager는 일관된 인터페이스와 동작 방식을 제공하여 상위 레이어(Bundle API)에서 쉽게 조합할 수 있도록 설계되었습니다.

### 설계 원칙

1. **멱등성 보장**: 동일한 요청을 여러 번 호출해도 결과가 동일
2. **비동기 처리**: FastAPI와의 통합을 위한 async/await 패턴
3. **명시적 예외**: 각 리소스별 커스텀 예외로 명확한 오류 처리
4. **순서 보장**: 리소스 간 의존성을 고려한 생성/삭제 순서
5. **정책 강제**: 네이밍, 레이블, 권한 등의 플랫폼 정책 적용
6. **Vault 통합**: Kubernetes Secret 대신 Vault 기반 Secret 관리

---

## 공통 특징

### 모든 Manager가 제공하는 기본 메서드

| 메서드 | 설명 | 멱등성 |
|--------|------|--------|
| `create_*()` | 리소스 생성 (이미 존재하면 기존 리소스 반환) | ✅ |
| `get_*()` | 리소스 조회 (없으면 None 반환) | ✅ |
| `delete_*()` | 리소스 삭제 (존재하지 않으면 예외 또는 True) | ⚠️ |
| `list_*()` | 리소스 목록 조회 | ✅ |
| `exists()` | 리소스 존재 여부 확인 | ✅ |
| `update_labels()` | 레이블 업데이트 (merge/replace 모드) | ✅ |

### 공통 파라미터

- **k8s_client**: `KubernetesClient` 인스턴스 (의존성 주입)
- **logger**: `Logger` 인스턴스 (선택적, 기본값: 전역 로거)
- **grace_period_seconds**: 삭제 시 유예 기간 (선택적)
- **label_selector**: 목록 조회 시 레이블 필터링
- **field_selector**: 목록 조회 시 필드 필터링

### 공통 예외 처리

- **409 Conflict**: 동시 생성 시 재조회하여 기존 리소스 반환
- **404 Not Found**: 조회 시 None 반환, 삭제 시 예외 발생 또는 True 반환
- **500 Internal Server Error**: 명시적 예외로 변환하여 상세 정보 제공

---

## Manager 목록

### NamespaceManager

**경로**: `infra/kubernetes/managers/namespace/manager.py`

#### 역할
Kubernetes Namespace 리소스의 전체 라이프사이클을 관리합니다. Namespace는 다른 모든 리소스의 **격리 단위**이며, 가장 먼저 생성되어야 하는 리소스입니다.

#### 주요 기능

##### 1. create_namespace()
```python
async def create_namespace(
    name: str,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None
) -> V1Namespace
```

**기능**: Namespace 생성 (멱등성 보장)
- 이미 존재하면 기존 Namespace 반환
- 레이블/어노테이션 설정 가능
- 409 Conflict 시 자동 재조회

**사용 예시**:
```python
namespace = await namespace_manager.create_namespace(
    name="student-1234",
    labels={
        "madp.io/tenant": "student",
        "madp.io/student-id": "1234"
    },
    annotations={
        "description": "Student workspace"
    }
)
```

##### 2. get_namespace()
```python
async def get_namespace(name: str) -> Optional[V1Namespace]
```

**기능**: Namespace 조회
- 존재하지 않으면 None 반환
- 404 외의 오류는 예외 발생

##### 3. delete_namespace()
```python
async def delete_namespace(
    name: str,
    grace_period_seconds: Optional[int] = None
) -> bool
```

**기능**: Namespace 삭제
- 존재하지 않으면 예외 발생
- grace_period로 유예 기간 설정 가능
- Namespace 삭제 시 내부의 모든 리소스도 함께 삭제됨 (Cascading Delete)

##### 4. get_namespace_status()
```python
async def get_namespace_status(name: str) -> str
```

**기능**: Namespace 상태 조회
- 반환값: "Active", "Terminating", "Unknown"
- Terminating 상태는 삭제 진행 중을 의미

**사용 예시**:
```python
status = await namespace_manager.get_namespace_status("student-1234")
if status == "Terminating":
    # Namespace가 삭제 중이므로 대기
    await asyncio.sleep(5)
```

#### 특징
- **Cascading Delete**: Namespace 삭제 시 모든 하위 리소스 자동 삭제
- **Status 추적**: Active/Terminating 상태 확인 가능
- **플랫폼 정책**: 네이밍 규칙, 필수 레이블 강제 가능 (상위 레이어에서)

---

### ServiceAccountManager

**경로**: `infra/kubernetes/managers/serviceaccount/manager.py`

#### 역할
Kubernetes ServiceAccount 리소스를 관리합니다. ServiceAccount는 Pod가 **Kubernetes API 또는 Vault에 접근할 때 사용하는 ID**입니다.

#### 주요 기능

##### 1. create_service_account()
```python
async def create_service_account(
    name: str,
    namespace: str,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    image_pull_secrets: Optional[List[str]] = None
) -> V1ServiceAccount
```

**기능**: ServiceAccount 생성
- ImagePullSecret 자동 연결 지원
- Vault 연동을 위한 어노테이션 설정 가능

**사용 예시**:
```python
sa = await sa_manager.create_service_account(
    name="app-sa",
    namespace="student-1234",
    labels={"app": "myapp"},
    annotations={
        "vault.hashicorp.com/role": "myapp-role",
        "vault.hashicorp.com/agent-inject": "true"
    },
    image_pull_secrets=["docker-registry-secret"]
)
```

##### 2. add_image_pull_secret()
```python
async def add_image_pull_secret(
    name: str,
    namespace: str,
    secret_name: str
) -> V1ServiceAccount
```

**기능**: ImagePullSecret 추가 (멱등성)
- 이미 존재하면 기존 ServiceAccount 반환
- Private Registry 접근을 위한 Secret 연결

**사용 예시**:
```python
sa = await sa_manager.add_image_pull_secret(
    name="app-sa",
    namespace="student-1234",
    secret_name="harbor-registry"
)
```

##### 3. update_annotations()
```python
async def update_annotations(
    name: str,
    namespace: str,
    annotations: Dict[str, str],
    merge: bool = True
) -> V1ServiceAccount
```

**기능**: 어노테이션 업데이트
- merge=True: 기존 어노테이션과 병합
- merge=False: 기존 어노테이션 전체 교체
- Vault Agent 설정 변경 시 주로 사용

#### 특징
- **Vault 연동**: 어노테이션으로 Vault Agent Injector 설정
- **ImagePullSecret 관리**: Private Registry 접근 권한 관리
- **Token 자동 생성**: Kubernetes가 자동으로 Token Secret 생성 (1.24+부터는 명시적 요청 필요)

---

### RoleManager

**경로**: `infra/kubernetes/managers/role/manager.py`

#### 역할
Kubernetes Role 리소스를 관리합니다. Role은 **Namespace 내에서의 권한**을 정의하는 RBAC 리소스입니다.

#### 주요 기능

##### 1. create_role()
```python
async def create_role(
    name: str,
    namespace: str,
    rules: List[Dict[str, List[str]]],
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None
) -> V1Role
```

**기능**: Role 생성
- PolicyRule 리스트로 권한 정의
- apiGroups, resources, verbs, resourceNames 지원

**사용 예시**:
```python
role = await role_manager.create_role(
    name="pod-reader",
    namespace="student-1234",
    rules=[
        {
            "apiGroups": [""],  # core API group
            "resources": ["pods", "pods/log"],
            "verbs": ["get", "list", "watch"]
        },
        {
            "apiGroups": ["apps"],
            "resources": ["deployments"],
            "verbs": ["get", "list"],
            "resourceNames": ["my-deployment"]  # 특정 리소스만 허용
        }
    ],
    labels={"madp.io/role-type": "read-only"}
)
```

##### 2. PolicyRule 구조
```python
{
    "apiGroups": [""],           # "" = core, "apps", "batch" 등
    "resources": ["pods"],       # 리소스 타입
    "verbs": ["get", "list"],    # 허용할 동작
    "resourceNames": ["pod-1"]   # (선택) 특정 리소스만 제한
}
```

**주요 Verbs**:
- **조회**: get, list, watch
- **생성**: create
- **수정**: update, patch
- **삭제**: delete, deletecollection
- **특수**: exec (Pod 접속), logs (로그 조회)

#### 특징
- **최소 권한 원칙**: 필요한 최소한의 권한만 부여
- **Namespace Scope**: 해당 Namespace 내에서만 유효
- **세밀한 제어**: resourceNames로 특정 리소스만 허용 가능

---

### RoleBindingManager

**경로**: `infra/kubernetes/managers/rolebinding/manager.py`

#### 역할
Kubernetes RoleBinding 리소스를 관리합니다. RoleBinding은 **Role과 Subject(사용자/그룹/ServiceAccount)를 연결**하는 RBAC 리소스입니다.

#### 주요 기능

##### 1. create_rolebinding()
```python
async def create_rolebinding(
    name: str,
    namespace: str,
    role_name: str,
    subjects: List[Dict[str, str]],
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None
) -> V1RoleBinding
```

**기능**: RoleBinding 생성
- Role과 Subject를 연결
- 여러 Subject에게 동일한 Role 부여 가능

**사용 예시**:
```python
rb = await rb_manager.create_rolebinding(
    name="pod-reader-binding",
    namespace="student-1234",
    role_name="pod-reader",
    subjects=[
        {
            "kind": "ServiceAccount",
            "name": "app-sa",
            "namespace": "student-1234"
        },
        {
            "kind": "User",
            "name": "student@example.com",
            "apiGroup": "rbac.authorization.k8s.io"
        }
    ]
)
```

##### 2. add_subject()
```python
async def add_subject(
    name: str,
    namespace: str,
    subject: Dict[str, str]
) -> V1RoleBinding
```

**기능**: RoleBinding에 Subject 추가 (멱등성)
- 이미 존재하면 기존 RoleBinding 반환
- 권한 부여 대상 추가 시 사용

**사용 예시**:
```python
rb = await rb_manager.add_subject(
    name="pod-reader-binding",
    namespace="student-1234",
    subject={
        "kind": "ServiceAccount",
        "name": "new-app-sa",
        "namespace": "student-1234"
    }
)
```

##### 3. Subject 타입

**ServiceAccount**:
```python
{
    "kind": "ServiceAccount",
    "name": "app-sa",
    "namespace": "student-1234"  # 필수
}
```

**User** (OIDC, Certificate 등):
```python
{
    "kind": "User",
    "name": "user@example.com",
    "apiGroup": "rbac.authorization.k8s.io"
}
```

**Group**:
```python
{
    "kind": "Group",
    "name": "students",
    "apiGroup": "rbac.authorization.k8s.io"
}
```

#### 특징
- **다대다 관계**: 하나의 Role을 여러 Subject에게 부여 가능
- **Namespace Scope**: RoleBinding은 해당 Namespace 내에서만 유효
- **Subject 추가 지원**: 기존 RoleBinding에 새로운 Subject 추가 가능

---

### ConfigMapManager

**경로**: `infra/kubernetes/managers/configmap/manager.py`

#### 역할
Kubernetes ConfigMap 리소스를 관리합니다. ConfigMap은 **애플리케이션 설정을 Key-Value 형태로 저장**하는 리소스입니다.

#### 주요 기능

##### 1. create_configmap()
```python
async def create_configmap(
    name: str,
    namespace: str,
    data: Optional[Dict[str, str]] = None,
    binary_data: Optional[Dict[str, bytes]] = None,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None
) -> V1ConfigMap
```

**기능**: ConfigMap 생성 (멱등성)
- 문자열 데이터(data)와 바이너리 데이터(binary_data) 모두 지원
- Pod에서 환경 변수 또는 파일로 마운트 가능

**사용 예시**:
```python
cm = await cm_manager.create_configmap(
    name="app-config",
    namespace="student-1234",
    data={
        "DATABASE_HOST": "postgres.default.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "LOG_LEVEL": "INFO",
        "app.properties": """
server.port=8080
spring.application.name=myapp
        """
    },
    labels={"app": "myapp"}
)
```

##### 2. update_data()
```python
async def update_data(
    name: str,
    namespace: str,
    data: Dict[str, str],
    merge: bool = True
) -> V1ConfigMap
```

**기능**: ConfigMap 데이터 업데이트
- merge=True: 기존 데이터와 병합
- merge=False: 기존 데이터 전체 교체

**사용 예시**:
```python
# 기존 데이터 유지하면서 LOG_LEVEL만 변경
cm = await cm_manager.update_data(
    name="app-config",
    namespace="student-1234",
    data={"LOG_LEVEL": "DEBUG"},
    merge=True
)
```

##### 3. Pod에서 ConfigMap 사용

**환경 변수로 사용**:
```python
# Deployment/StatefulSet에서
env_from = [
    V1EnvFromSource(
        config_map_ref=V1ConfigMapEnvSource(name="app-config")
    )
]
```

**볼륨으로 마운트**:
```python
volumes = [
    V1Volume(
        name="config-volume",
        config_map=V1ConfigMapVolumeSource(name="app-config")
    )
]
volume_mounts = [
    V1VolumeMount(
        name="config-volume",
        mount_path="/etc/config"
    )
]
```

#### 특징
- **Hot Reload**: ConfigMap 변경 시 Pod 재시작 없이 반영 가능 (볼륨 마운트 시)
- **바이너리 지원**: binary_data로 바이너리 파일 저장 가능
- **크기 제한**: 단일 ConfigMap은 최대 1MB

---

### SecretManager

**경로**: `infra/kubernetes/managers/secret/manager.py`

#### 역할
**Vault 기반 Secret 접근 구조**를 관리하는 클래스입니다. **Kubernetes Secret 리소스를 직접 생성하지 않고**, Vault와의 연동 구조를 관리합니다.

#### 핵심 개념

M-ADP에서는 민감한 데이터를 Kubernetes Secret에 저장하지 않고 **Vault**에 저장합니다:
- **Kubernetes Secret**: 생성하지 않음 ❌
- **Vault**: 실제 Secret 값 저장 ✅
- **Vault Agent/CSI**: Pod에서 Vault Secret 접근 ✅

SecretManager는 다음을 관리:
1. Vault Policy/Role 생성
2. ServiceAccount ↔ Vault 바인딩
3. Workload(Deployment/StatefulSet)에 Vault 설정 주입

#### 주요 기능

##### 1. bind_serviceaccount_to_vault()
```python
async def bind_serviceaccount_to_vault(
    service_account_name: str,
    namespace: str,
    vault_role_name: str,
    secret_paths: List[str],
    capabilities: List[str] = ["read"]
) -> Dict[str, Any]
```

**기능**: ServiceAccount를 Vault Role에 바인딩
- Vault Policy 자동 생성 (secret_paths 기반)
- Vault Role 생성 (ServiceAccount와 Policy 연결)
- ServiceAccount에 annotation 추가

**사용 예시**:
```python
binding = await secret_manager.bind_serviceaccount_to_vault(
    service_account_name="app-sa",
    namespace="student-1234",
    vault_role_name="student-1234-app-role",
    secret_paths=[
        "secret/data/app/database",
        "secret/data/app/api-keys"
    ],
    capabilities=["read"]
)
# 반환값:
# {
#     "vault_role": "student-1234-app-role",
#     "vault_policy": "student-1234-app-sa-policy",
#     "service_account": "student-1234/app-sa",
#     "secret_paths": ["secret/data/app/database", ...]
# }
```

##### 2. inject_vault_agent_to_deployment()
```python
async def inject_vault_agent_to_deployment(
    deployment_name: str,
    namespace: str,
    vault_role: str,
    secret_configs: List[Dict[str, str]]
) -> V1Deployment
```

**기능**: Deployment에 Vault Agent Injector annotations 추가
- Pod Template에 Vault 관련 annotations 추가
- Vault Agent Sidecar 자동 주입 (Vault Agent Injector가 처리)

**사용 예시**:
```python
deployment = await secret_manager.inject_vault_agent_to_deployment(
    deployment_name="myapp",
    namespace="student-1234",
    vault_role="student-1234-app-role",
    secret_configs=[
        {
            "name": "db-creds",
            "path": "secret/data/app/database"
        },
        {
            "name": "api-key",
            "path": "secret/data/app/api-keys"
        }
    ]
)
# Pod 생성 시 Vault Agent가 자동으로 주입되고
# /vault/secrets/db-creds, /vault/secrets/api-key 파일에
# Secret 값이 기록됨
```

##### 3. setup_secret_access()
```python
async def setup_secret_access(
    service_account_name: str,
    namespace: str,
    secret_paths: List[str],
    workload_name: Optional[str] = None,
    workload_type: Optional[str] = None,  # "deployment" or "statefulset"
    secret_configs: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]
```

**기능**: Secret 접근을 위한 전체 설정 (통합 헬퍼)
- 한 번의 호출로 Vault Policy, Role, ServiceAccount 바인딩, Workload 설정 주입까지 처리

**사용 예시**:
```python
result = await secret_manager.setup_secret_access(
    service_account_name="app-sa",
    namespace="student-1234",
    secret_paths=["secret/data/app/database"],
    workload_name="myapp",
    workload_type="deployment",
    secret_configs=[
        {"name": "db-creds", "path": "secret/data/app/database"}
    ]
)
```

##### 4. Vault Policy/Role 직접 관리
```python
# Vault Policy 생성
await secret_manager.create_vault_policy(
    policy_name="my-policy",
    secret_paths=["secret/data/app/*"],
    capabilities=["read", "list"]
)

# Vault Role 생성
await secret_manager.create_vault_role(
    role_name="my-role",
    bound_service_account_names=["app-sa"],
    bound_service_account_namespaces=["student-1234"],
    policies=["my-policy"],
    ttl="1h",
    max_ttl="24h"
)
```

#### 특징
- **No K8s Secret**: Kubernetes Secret 리소스를 생성하지 않음 (보안 강화)
- **Vault 중심**: 모든 Secret은 Vault에만 저장
- **자동 주입**: Vault Agent Injector가 Pod에 Sidecar 자동 추가
- **동적 Secret**: Vault의 동적 Secret 기능 활용 가능 (DB 크레덴셜 등)

---

### DeploymentManager

**경로**: `infra/kubernetes/managers/deployment/manager.py`

#### 역할
Kubernetes Deployment 리소스를 관리합니다. Deployment는 **Stateless 애플리케이션의 배포 및 업데이트**를 관리하는 리소스입니다.

#### 주요 기능

##### 1. create_deployment()
```python
async def create_deployment(
    name: str,
    namespace: str,
    containers: List[V1Container],
    replicas: int = 1,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    selector_labels: Optional[Dict[str, str]] = None,
    pod_labels: Optional[Dict[str, str]] = None,
    pod_annotations: Optional[Dict[str, str]] = None
) -> V1Deployment
```

**기능**: Deployment 생성 (멱등성)
- 컨테이너 리스트로 Pod Template 정의
- 레플리카 수 지정
- Pod와 Deployment의 레이블/어노테이션 분리 설정 가능

**사용 예시**:
```python
from kubernetes_asyncio.client import V1Container, V1EnvVar, V1ResourceRequirements

deployment = await deployment_manager.create_deployment(
    name="myapp",
    namespace="student-1234",
    replicas=3,
    containers=[
        V1Container(
            name="app",
            image="myapp:v1.0.0",
            ports=[V1ContainerPort(container_port=8080)],
            env=[
                V1EnvVar(name="ENV", value="production"),
                V1EnvVar(name="LOG_LEVEL", value="INFO")
            ],
            resources=V1ResourceRequirements(
                requests={"cpu": "100m", "memory": "128Mi"},
                limits={"cpu": "500m", "memory": "512Mi"}
            )
        )
    ],
    labels={"app": "myapp", "version": "v1"},
    pod_annotations={
        "vault.hashicorp.com/agent-inject": "true",
        "vault.hashicorp.com/role": "myapp-role"
    }
)
```

##### 2. update_replicas()
```python
async def update_replicas(
    name: str,
    namespace: str,
    replicas: int
) -> V1Deployment
```

**기능**: 레플리카 수 변경 (스케일링)
- 수평 확장/축소
- HPA(HorizontalPodAutoscaler)와 함께 사용 가능

**사용 예시**:
```python
# 스케일 아웃
await deployment_manager.update_replicas("myapp", "student-1234", replicas=5)

# 스케일 인
await deployment_manager.update_replicas("myapp", "student-1234", replicas=1)
```

##### 3. get_deployment_status()
```python
async def get_deployment_status(
    name: str,
    namespace: str
) -> Optional[Dict[str, any]]
```

**기능**: Deployment 상태 조회
- 레플리카 준비 상태 확인
- 롤아웃 진행 상황 확인

**반환 예시**:
```python
{
    "replicas": 3,              # 전체 레플리카 수
    "ready_replicas": 3,        # 준비된 레플리카 수
    "available_replicas": 3,    # 사용 가능한 레플리카 수
    "updated_replicas": 3,      # 업데이트된 레플리카 수
    "unavailable_replicas": 0,  # 사용 불가능한 레플리카 수
    "conditions": [
        {
            "type": "Progressing",
            "status": "True",
            "reason": "NewReplicaSetAvailable",
            "message": "ReplicaSet \"myapp-xyz\" has successfully progressed."
        },
        {
            "type": "Available",
            "status": "True",
            "reason": "MinimumReplicasAvailable",
            "message": "Deployment has minimum availability."
        }
    ]
}
```

#### 특징
- **Rolling Update**: 무중단 배포 지원 (기본 전략)
- **Rollback**: 이전 버전으로 롤백 가능 (kubectl rollout undo)
- **자동 복구**: Pod 장애 시 자동으로 새 Pod 생성
- **Stateless**: 상태를 저장하지 않는 애플리케이션에 적합

#### 사용 시나리오
- 웹 서버, API 서버
- 마이크로서비스
- Worker 프로세스 (큐 처리 등)

---

### StatefulSetManager

**경로**: `infra/kubernetes/managers/statefulset/manager.py`

#### 역할
Kubernetes StatefulSet 리소스를 관리합니다. StatefulSet은 **Stateful 애플리케이션의 배포 및 관리**를 위한 리소스입니다.

#### Deployment와의 차이점

| 특성 | Deployment | StatefulSet |
|------|-----------|-------------|
| Pod 이름 | 랜덤 (myapp-xyz-123) | 순서 보장 (myapp-0, myapp-1, myapp-2) |
| Pod 생성 순서 | 동시 생성 | 순차 생성 (0 → 1 → 2) |
| Pod 삭제 순서 | 랜덤 | 역순 삭제 (2 → 1 → 0) |
| 네트워크 ID | 불안정 | 안정적 (myapp-0.svc.ns.svc.cluster.local) |
| 스토리지 | 공유 | 개별 PVC (Pod마다 별도) |
| 사용 사례 | Stateless 앱 | 데이터베이스, 큐, 분산 시스템 |

#### 주요 기능

##### 1. create_statefulset()
```python
async def create_statefulset(
    name: str,
    namespace: str,
    service_name: str,  # Headless Service 이름
    replicas: int,
    selector: Dict[str, str],
    containers: List[V1Container],
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    volume_claim_templates: Optional[List[V1PersistentVolumeClaim]] = None,
    update_strategy: Optional[str] = "RollingUpdate",
    pod_management_policy: Optional[str] = "OrderedReady"
) -> V1StatefulSet
```

**기능**: StatefulSet 생성 (멱등성)
- Headless Service 필수 (안정적인 네트워크 ID 제공)
- VolumeClaimTemplate로 각 Pod마다 별도 PVC 생성

**사용 예시**:
```python
from kubernetes_asyncio.client import (
    V1Container, V1StatefulSet, V1PersistentVolumeClaim,
    V1PersistentVolumeClaimSpec, V1ResourceRequirements
)

# 1. 먼저 Headless Service 생성 (ServiceManager 사용)
headless_svc = await service_manager.create_service(
    name="redis-svc",
    namespace="student-1234",
    selector={"app": "redis"},
    ports=[{"port": 6379, "target_port": 6379, "name": "redis"}],
    service_type="ClusterIP",
    cluster_ip="None"  # Headless Service
)

# 2. StatefulSet 생성
statefulset = await statefulset_manager.create_statefulset(
    name="redis",
    namespace="student-1234",
    service_name="redis-svc",  # Headless Service 이름
    replicas=3,
    selector={"app": "redis"},
    containers=[
        V1Container(
            name="redis",
            image="redis:7-alpine",
            ports=[V1ContainerPort(container_port=6379, name="redis")],
            volume_mounts=[
                V1VolumeMount(name="data", mount_path="/data")
            ]
        )
    ],
    volume_claim_templates=[
        V1PersistentVolumeClaim(
            metadata=V1ObjectMeta(name="data"),
            spec=V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=V1ResourceRequirements(
                    requests={"storage": "10Gi"}
                )
            )
        )
    ],
    update_strategy="RollingUpdate",
    pod_management_policy="OrderedReady"
)

# Pod 이름: redis-0, redis-1, redis-2
# PVC 이름: data-redis-0, data-redis-1, data-redis-2
# 네트워크: redis-0.redis-svc.student-1234.svc.cluster.local
```

##### 2. scale_statefulset()
```python
async def scale_statefulset(
    name: str,
    namespace: str,
    replicas: int
) -> V1StatefulSet
```

**기능**: StatefulSet 스케일 조정
- 순차적 스케일 아웃/인
- 스케일 인 시 PVC는 자동 삭제되지 않음 (데이터 보호)

**사용 예시**:
```python
# 스케일 아웃: redis-3 생성 (순차적)
await statefulset_manager.scale_statefulset("redis", "student-1234", replicas=4)

# 스케일 인: redis-3 삭제 (역순)
await statefulset_manager.scale_statefulset("redis", "student-1234", replicas=3)
# 주의: data-redis-3 PVC는 삭제되지 않음
```

##### 3. get_statefulset_status()
```python
async def get_statefulset_status(
    name: str,
    namespace: str
) -> Optional[Dict[str, any]]
```

**기능**: StatefulSet 상태 조회

**반환 예시**:
```python
{
    "replicas": 3,
    "ready_replicas": 3,
    "current_replicas": 3,
    "updated_replicas": 3,
    "current_revision": "redis-5d8f9c7b8c",
    "update_revision": "redis-5d8f9c7b8c"
}
```

##### 4. is_ready()
```python
async def is_ready(
    name: str,
    namespace: str
) -> bool
```

**기능**: StatefulSet 준비 상태 확인
- 모든 Pod가 Ready 상태인지 확인
- 배포 완료 대기 시 유용

#### 특징
- **안정적인 네트워크 ID**: Pod 재시작 후에도 동일한 DNS 이름
- **순서 보장**: Pod 생성/삭제 순서 보장
- **개별 스토리지**: 각 Pod마다 별도 PVC
- **StatefulSet 삭제 시 PVC 보존**: 데이터 손실 방지

#### Update Strategies

**RollingUpdate** (기본):
- 역순으로 하나씩 업데이트 (N-1 → 0)
- 각 Pod가 Ready 상태가 된 후 다음 Pod 업데이트

**OnDelete**:
- 수동 업데이트
- Pod를 직접 삭제해야 새 버전으로 생성됨

#### 사용 시나리오
- 데이터베이스 (MySQL, PostgreSQL, MongoDB)
- 메시지 큐 (Kafka, RabbitMQ)
- 분산 캐시 (Redis Cluster)
- 분산 스토리지 (Cassandra, Elasticsearch)

---

### ServiceManager

**경로**: `infra/kubernetes/managers/service/manager.py`

#### 역할
Kubernetes Service 리소스를 관리합니다. Service는 **Pod에 대한 안정적인 네트워크 엔드포인트**를 제공하는 리소스입니다.

#### Service 타입

| 타입 | 설명 | 사용 사례 |
|------|------|-----------|
| ClusterIP | 클러스터 내부에서만 접근 가능 (기본값) | 내부 서비스 간 통신 |
| NodePort | 각 Node의 특정 포트로 접근 가능 | 개발/테스트 환경 |
| LoadBalancer | 외부 로드밸런서 생성 (클라우드) | 프로덕션 외부 노출 |
| ExternalName | 외부 DNS로 리다이렉트 | 외부 서비스 참조 |

#### 주요 기능

##### 1. create_service()
```python
async def create_service(
    name: str,
    namespace: str,
    selector: Dict[str, str],
    ports: List[Dict[str, any]],
    service_type: str = "ClusterIP",
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    cluster_ip: Optional[str] = None,
    external_ips: Optional[List[str]] = None
) -> V1Service
```

**기능**: Service 생성 (멱등성)
- selector로 트래픽을 받을 Pod 지정
- 여러 포트 매핑 지원

**사용 예시**:

**ClusterIP Service (내부 통신)**:
```python
svc = await service_manager.create_service(
    name="myapp-svc",
    namespace="student-1234",
    selector={"app": "myapp"},  # app=myapp 레이블을 가진 Pod로 트래픽 전달
    ports=[
        {
            "name": "http",
            "port": 80,           # Service 포트
            "target_port": 8080,  # Pod 포트
            "protocol": "TCP"
        },
        {
            "name": "metrics",
            "port": 9090,
            "target_port": 9090,
            "protocol": "TCP"
        }
    ],
    service_type="ClusterIP"
)
# 접근: myapp-svc.student-1234.svc.cluster.local:80
```

**Headless Service (StatefulSet용)**:
```python
headless_svc = await service_manager.create_service(
    name="redis-svc",
    namespace="student-1234",
    selector={"app": "redis"},
    ports=[{"port": 6379, "target_port": 6379}],
    service_type="ClusterIP",
    cluster_ip="None"  # Headless
)
# 접근: redis-0.redis-svc.student-1234.svc.cluster.local:6379
```

**LoadBalancer Service (외부 노출)**:
```python
lb_svc = await service_manager.create_service(
    name="web-lb",
    namespace="student-1234",
    selector={"app": "web"},
    ports=[{"port": 80, "target_port": 8080}],
    service_type="LoadBalancer",
    annotations={
        "service.beta.kubernetes.io/aws-load-balancer-type": "nlb"
    }
)
# 외부 IP가 할당됨 (클라우드 로드밸런서)
```

##### 2. update_selector()
```python
async def update_selector(
    name: str,
    namespace: str,
    selector: Dict[str, str]
) -> V1Service
```

**기능**: Service의 트래픽 대상 변경
- Blue-Green 배포, Canary 배포 시 사용

**사용 예시**:
```python
# Blue-Green 배포
# 1. Green 버전 배포
green_deployment = await deployment_manager.create_deployment(
    name="myapp-green",
    namespace="student-1234",
    containers=[...],
    labels={"app": "myapp", "version": "green"}
)

# 2. Service를 Green으로 전환
await service_manager.update_selector(
    name="myapp-svc",
    namespace="student-1234",
    selector={"app": "myapp", "version": "green"}
)
```

##### 3. get_service_endpoints()
```python
async def get_service_endpoints(
    name: str,
    namespace: str
) -> Optional[str]
```

**기능**: Service의 엔드포인트 조회
- ClusterIP 또는 LoadBalancer IP 반환

**사용 예시**:
```python
endpoint = await service_manager.get_service_endpoints("myapp-svc", "student-1234")
# ClusterIP: "10.96.10.123"
# LoadBalancer: "52.123.45.67" (External IP)
```

##### 4. update_annotations()
```python
async def update_annotations(
    name: str,
    namespace: str,
    annotations: Dict[str, str],
    merge: bool = True
) -> V1Service
```

**기능**: Service 어노테이션 업데이트
- 클라우드 로드밸런서 설정 변경 시 주로 사용

#### Port 매핑 구조

```python
{
    "name": "http",          # 포트 이름 (선택적)
    "port": 80,              # Service 포트 (외부에서 접근)
    "target_port": 8080,     # Pod 포트 (컨테이너 포트)
    "protocol": "TCP",       # TCP 또는 UDP
    "node_port": 30080       # NodePort 타입일 때만 (선택적)
}
```

#### 특징
- **자동 로드밸런싱**: selector에 매칭되는 모든 Pod로 트래픽 분산
- **Service Discovery**: DNS로 Service 이름 해석 가능
- **안정적인 IP**: Pod IP는 변경되지만 Service IP는 고정
- **Health Check**: Readiness Probe 실패한 Pod는 자동 제외

#### 사용 시나리오
- **ClusterIP**: 마이크로서비스 간 통신
- **Headless**: StatefulSet의 각 Pod에 직접 접근
- **LoadBalancer**: 외부 사용자에게 서비스 노출

---

### PodManager

**경로**: `infra/kubernetes/managers/pod/manager.py`

#### 역할
Kubernetes Pod 리소스를 **조회 및 관찰**하는 클래스입니다.

**중요**: Pod는 **직접 생성/삭제하지 않습니다**. Pod는 Deployment, StatefulSet 등의 컨트롤러를 통해 관리되어야 합니다.

#### 설계 의도

Pod를 직접 생성하면:
- ❌ Pod 장애 시 자동 복구 없음
- ❌ 롤링 업데이트 불가능
- ❌ 스케일링 불가능
- ❌ 선언적 관리 불가능

따라서 PodManager는 **조회/관찰 전용**입니다.

#### 주요 기능

##### 1. get_pod()
```python
async def get_pod(
    name: str,
    namespace: str
) -> Optional[V1Pod]
```

**기능**: 특정 Pod 조회

**사용 예시**:
```python
pod = await pod_manager.get_pod("myapp-xyz-123", "student-1234")
if pod:
    print(f"Pod IP: {pod.status.pod_ip}")
    print(f"Node: {pod.spec.node_name}")
```

##### 2. list_pods()
```python
async def list_pods(
    namespace: Optional[str] = None,
    label_selector: Optional[str] = None,
    field_selector: Optional[str] = None
) -> List[V1Pod]
```

**기능**: Pod 목록 조회
- label_selector, field_selector로 필터링 가능

**사용 예시**:
```python
# 특정 애플리케이션의 모든 Pod
pods = await pod_manager.list_pods(
    namespace="student-1234",
    label_selector="app=myapp"
)

# 특정 Node의 모든 Pod
pods = await pod_manager.list_pods(
    field_selector="spec.nodeName=node-1"
)

# Running 상태의 Pod만
pods = await pod_manager.list_pods(
    field_selector="status.phase=Running"
)
```

##### 3. get_pod_status()
```python
async def get_pod_status(
    name: str,
    namespace: str
) -> Optional[Dict[str, any]]
```

**기능**: Pod의 상세 상태 조회

**반환 예시**:
```python
{
    "phase": "Running",  # Pending, Running, Succeeded, Failed, Unknown
    "pod_ip": "10.244.1.5",
    "host_ip": "192.168.1.10",
    "start_time": "2025-01-15T10:30:00Z",
    "conditions": [
        {
            "type": "Initialized",
            "status": "True",
            "reason": "PodCompleted",
            "message": "All init containers have completed"
        },
        {
            "type": "Ready",
            "status": "True",
            "reason": "ContainersReady",
            "message": "All containers are ready"
        },
        {
            "type": "ContainersReady",
            "status": "True",
            "reason": "ContainersReady",
            "message": "All containers are ready"
        },
        {
            "type": "PodScheduled",
            "status": "True",
            "reason": "Scheduled",
            "message": "Pod scheduled on node-1"
        }
    ],
    "container_statuses": [
        {
            "name": "app",
            "ready": True,
            "restart_count": 0,
            "image": "myapp:v1.0.0",
            "state": {
                "state": "Running",
                "started_at": "2025-01-15T10:30:05Z"
            }
        }
    ]
}
```

##### 4. get_pod_logs()
```python
async def get_pod_logs(
    name: str,
    namespace: str,
    container: Optional[str] = None,
    tail_lines: Optional[int] = None,
    since_seconds: Optional[int] = None,
    timestamps: bool = False
) -> Optional[str]
```

**기능**: Pod 로그 조회

**사용 예시**:
```python
# 전체 로그
logs = await pod_manager.get_pod_logs("myapp-xyz-123", "student-1234")

# 최근 100줄만
logs = await pod_manager.get_pod_logs(
    "myapp-xyz-123",
    "student-1234",
    tail_lines=100
)

# 최근 10분간의 로그
logs = await pod_manager.get_pod_logs(
    "myapp-xyz-123",
    "student-1234",
    since_seconds=600
)

# 타임스탬프 포함
logs = await pod_manager.get_pod_logs(
    "myapp-xyz-123",
    "student-1234",
    timestamps=True
)

# 특정 컨테이너 로그 (Multi-container Pod)
logs = await pod_manager.get_pod_logs(
    "myapp-xyz-123",
    "student-1234",
    container="sidecar"
)
```

##### 5. list_pods_by_owner()
```python
async def list_pods_by_owner(
    owner_name: str,
    owner_kind: str,  # "Deployment", "StatefulSet", "Job" 등
    namespace: str
) -> List[V1Pod]
```

**기능**: 특정 컨트롤러가 소유한 Pod 목록 조회

**사용 예시**:
```python
# Deployment의 모든 Pod 조회
pods = await pod_manager.list_pods_by_owner(
    owner_name="myapp",
    owner_kind="Deployment",
    namespace="student-1234"
)

# StatefulSet의 모든 Pod 조회
pods = await pod_manager.list_pods_by_owner(
    owner_name="redis",
    owner_kind="StatefulSet",
    namespace="student-1234"
)
```

#### Pod Phase (상태)

| Phase | 의미 |
|-------|------|
| Pending | 스케줄링 대기 또는 이미지 다운로드 중 |
| Running | Pod가 Node에 바인딩되고 모든 컨테이너 생성됨 |
| Succeeded | 모든 컨테이너가 성공적으로 종료됨 (Job에서 주로 사용) |
| Failed | 하나 이상의 컨테이너가 실패로 종료됨 |
| Unknown | Pod 상태를 확인할 수 없음 (Node 통신 장애 등) |

#### Container State

| State | 의미 |
|-------|------|
| Waiting | 컨테이너가 아직 시작되지 않음 (이미지 Pull, Init Container 대기 등) |
| Running | 컨테이너가 정상 실행 중 |
| Terminated | 컨테이너가 종료됨 (정상 또는 오류) |

#### 특징
- **Read-Only**: 생성/삭제 기능 없음 (조회/관찰만)
- **로그 접근**: 컨테이너 로그 조회 가능
- **상태 추적**: Phase, Conditions, Container State 확인
- **Owner 추적**: OwnerReferences로 상위 컨트롤러 확인

#### 사용 시나리오
- 애플리케이션 디버깅 (로그 조회)
- Pod 상태 모니터링
- Deployment/StatefulSet의 Pod 확인
- 장애 분석 (Termination Reason 확인)

---

## 사용 패턴

### 패턴 1: 기본 리소스 생성 순서

Kubernetes 리소스는 **강한 순서 의존성**이 있습니다. 올바른 생성 순서:

```python
# 1. Namespace 생성 (가장 먼저)
namespace = await namespace_manager.create_namespace(
    name="student-1234",
    labels={"madp.io/tenant": "student"}
)

# 2. ConfigMap 생성 (설정)
configmap = await configmap_manager.create_configmap(
    name="app-config",
    namespace="student-1234",
    data={
        "DATABASE_HOST": "postgres.default.svc.cluster.local",
        "LOG_LEVEL": "INFO"
    }
)

# 3. ServiceAccount 생성
sa = await sa_manager.create_service_account(
    name="app-sa",
    namespace="student-1234"
)

# 4. Secret 접근 설정 (Vault)
await secret_manager.bind_serviceaccount_to_vault(
    service_account_name="app-sa",
    namespace="student-1234",
    vault_role_name="student-1234-app-role",
    secret_paths=["secret/data/app/database"]
)

# 5. Role 생성
role = await role_manager.create_role(
    name="pod-manager",
    namespace="student-1234",
    rules=[
        {
            "apiGroups": [""],
            "resources": ["pods"],
            "verbs": ["get", "list", "create", "delete"]
        }
    ]
)

# 6. RoleBinding 생성 (ServiceAccount와 Role 연결)
rb = await rb_manager.create_rolebinding(
    name="pod-manager-binding",
    namespace="student-1234",
    role_name="pod-manager",
    subjects=[
        {
            "kind": "ServiceAccount",
            "name": "app-sa",
            "namespace": "student-1234"
        }
    ]
)

# 7. Service 생성 (Deployment 전에 미리 생성 가능)
service = await service_manager.create_service(
    name="myapp-svc",
    namespace="student-1234",
    selector={"app": "myapp"},
    ports=[{"port": 80, "target_port": 8080}]
)

# 8. Deployment 생성
deployment = await deployment_manager.create_deployment(
    name="myapp",
    namespace="student-1234",
    replicas=3,
    containers=[
        V1Container(
            name="app",
            image="myapp:v1.0.0",
            env_from=[
                V1EnvFromSource(
                    config_map_ref=V1ConfigMapEnvSource(name="app-config")
                )
            ]
        )
    ],
    labels={"app": "myapp"}
)

# 9. Vault 설정 주입
await secret_manager.inject_vault_agent_to_deployment(
    deployment_name="myapp",
    namespace="student-1234",
    vault_role="student-1234-app-role",
    secret_configs=[
        {"name": "db-creds", "path": "secret/data/app/database"}
    ]
)
```

### 패턴 2: StatefulSet + Headless Service 패턴

```python
# 1. Headless Service 생성 (먼저)
headless_svc = await service_manager.create_service(
    name="redis-svc",
    namespace="student-1234",
    selector={"app": "redis"},
    ports=[{"port": 6379, "target_port": 6379}],
    service_type="ClusterIP",
    cluster_ip="None"  # Headless
)

# 2. StatefulSet 생성
statefulset = await statefulset_manager.create_statefulset(
    name="redis",
    namespace="student-1234",
    service_name="redis-svc",  # Headless Service 참조
    replicas=3,
    selector={"app": "redis"},
    containers=[
        V1Container(
            name="redis",
            image="redis:7-alpine",
            volume_mounts=[
                V1VolumeMount(name="data", mount_path="/data")
            ]
        )
    ],
    volume_claim_templates=[
        V1PersistentVolumeClaim(
            metadata=V1ObjectMeta(name="data"),
            spec=V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=V1ResourceRequirements(
                    requests={"storage": "10Gi"}
                )
            )
        )
    ]
)

# 3. Pod 상태 확인
pods = await pod_manager.list_pods_by_owner(
    owner_name="redis",
    owner_kind="StatefulSet",
    namespace="student-1234"
)
for pod in pods:
    status = await pod_manager.get_pod_status(pod.metadata.name, "student-1234")
    print(f"{pod.metadata.name}: {status['phase']}")
```

### 패턴 3: Blue-Green 배포

```python
# 1. Green 버전 배포
green_deployment = await deployment_manager.create_deployment(
    name="myapp-green",
    namespace="student-1234",
    replicas=3,
    containers=[
        V1Container(name="app", image="myapp:v2.0.0")
    ],
    labels={"app": "myapp", "version": "green"}
)

# 2. Green 버전 준비 완료 대기
import asyncio
while True:
    status = await deployment_manager.get_deployment_status("myapp-green", "student-1234")
    if status and status["ready_replicas"] == 3:
        break
    await asyncio.sleep(2)

# 3. Service를 Green으로 전환
await service_manager.update_selector(
    name="myapp-svc",
    namespace="student-1234",
    selector={"app": "myapp", "version": "green"}
)

# 4. (선택) 기존 Blue 버전 삭제
await deployment_manager.delete_deployment("myapp-blue", "student-1234")
```

### 패턴 4: Vault Secret 통합 워크플로우

```python
# 1. ServiceAccount 생성
sa = await sa_manager.create_service_account(
    name="app-sa",
    namespace="student-1234"
)

# 2. Vault 접근 설정 (한 번에)
await secret_manager.setup_secret_access(
    service_account_name="app-sa",
    namespace="student-1234",
    secret_paths=[
        "secret/data/app/database",
        "secret/data/app/api-keys"
    ],
    workload_name="myapp",
    workload_type="deployment",
    secret_configs=[
        {"name": "db-creds", "path": "secret/data/app/database"},
        {"name": "api-key", "path": "secret/data/app/api-keys"}
    ]
)

# 3. Deployment 생성 (Vault Agent Sidecar가 자동 주입됨)
deployment = await deployment_manager.create_deployment(
    name="myapp",
    namespace="student-1234",
    replicas=2,
    containers=[
        V1Container(
            name="app",
            image="myapp:v1.0.0",
            # Secret은 /vault/secrets/db-creds,
            # /vault/secrets/api-key 경로에 자동 마운트됨
        )
    ]
)
```

### 패턴 5: 멱등성 활용

동일한 요청을 여러 번 호출해도 안전:

```python
# 첫 호출: 생성됨
ns1 = await namespace_manager.create_namespace("test-ns")

# 두 번째 호출: 기존 리소스 반환 (오류 없음)
ns2 = await namespace_manager.create_namespace("test-ns")

assert ns1.metadata.uid == ns2.metadata.uid  # 동일한 리소스
```

### 패턴 6: 삭제 순서 (생성의 역순)

```python
# 1. Deployment 삭제 (먼저)
await deployment_manager.delete_deployment("myapp", "student-1234")

# 2. Service 삭제
await service_manager.delete_service("myapp-svc", "student-1234")

# 3. RoleBinding 삭제
await rb_manager.delete_rolebinding("pod-manager-binding", "student-1234")

# 4. Role 삭제
await role_manager.delete_role("pod-manager", "student-1234")

# 5. Vault 바인딩 해제
await secret_manager.unbind_serviceaccount_from_vault("app-sa", "student-1234")

# 6. ServiceAccount 삭제
await sa_manager.delete_service_account("app-sa", "student-1234")

# 7. ConfigMap 삭제
await configmap_manager.delete_configmap("app-config", "student-1234")

# 8. Namespace 삭제 (가장 마지막)
# Namespace 삭제 시 내부의 모든 리소스가 자동 삭제되므로
# 위 1~7단계는 사실상 불필요할 수 있음
await namespace_manager.delete_namespace("student-1234")
```

### 패턴 7: Pod 로그 모니터링

```python
# 1. Deployment의 모든 Pod 조회
pods = await pod_manager.list_pods_by_owner(
    owner_name="myapp",
    owner_kind="Deployment",
    namespace="student-1234"
)

# 2. 각 Pod의 로그 조회
for pod in pods:
    print(f"\n=== {pod.metadata.name} ===")
    logs = await pod_manager.get_pod_logs(
        name=pod.metadata.name,
        namespace="student-1234",
        tail_lines=50
    )
    print(logs)
    
    # 상태 확인
    status = await pod_manager.get_pod_status(
        name=pod.metadata.name,
        namespace="student-1234"
    )
    print(f"Phase: {status['phase']}")
    print(f"Ready: {status['container_statuses'][0]['ready']}")
```

---

## 예외 처리

### 예외 계층 구조

```
AppException (core/exception.py)
└── KubernetesResourceException (infra/kubernetes/exceptions.py)
    ├── ResourceCreationException
    │   ├── NamespaceCreationException
    │   ├── ServiceAccountCreationException
    │   ├── RoleCreationException
    │   ├── RoleBindingCreationException
    │   ├── ConfigMapCreationException
    │   ├── DeploymentCreationException
    │   ├── StatefulSetCreationException
    │   └── ServiceCreationException
    ├── ResourceReadException
    │   ├── NamespaceReadException
    │   ├── ServiceAccountReadException
    │   ├── RoleReadException
    │   ├── RoleBindingReadException
    │   ├── ConfigMapReadException
    │   ├── DeploymentReadException
    │   ├── StatefulSetReadException
    │   ├── ServiceReadException
    │   └── PodReadException
    ├── ResourceUpdateException
    │   ├── NamespaceUpdateException
    │   ├── ServiceAccountUpdateException
    │   ├── RoleUpdateException
    │   ├── RoleBindingUpdateException
    │   ├── ConfigMapUpdateException
    │   ├── DeploymentUpdateException
    │   ├── StatefulSetUpdateException
    │   └── ServiceUpdateException
    ├── ResourceDeletionException
    │   ├── NamespaceDeletionException
    │   ├── ServiceAccountDeletionException
    │   ├── RoleDeletionException
    │   ├── RoleBindingDeletionException
    │   ├── ConfigMapDeletionException
    │   ├── DeploymentDeletionException
    │   ├── StatefulSetDeletionException
    │   └── ServiceDeletionException
    ├── ResourceListException
    │   ├── NamespaceListException
    │   ├── ServiceAccountListException
    │   ├── RoleListException
    │   ├── RoleBindingListException
    │   ├── ConfigMapListException
    │   ├── DeploymentListException
    │   ├── StatefulSetListException
    │   ├── ServiceListException
    │   └── PodListException
    └── VaultException (infra/kubernetes/managers/secret/exceptions.py)
        ├── SecretAccessBindingException
        ├── SecretAccessUnbindingException
        └── VaultInjectionException
```

### 예외 처리 예시

```python
from infra.kubernetes.managers.deployment import (
    DeploymentManager,
    DeploymentCreationException,
)

try:
    deployment = await deployment_manager.create_deployment(
        name="myapp",
        namespace="student-1234",
        containers=[...]
    )
except DeploymentCreationException as e:
    # 생성 실패 시 상세 정보 확인
    logger.error(f"Deployment 생성 실패: {e.message}")
    logger.error(f"상태 코드: {e.status_code}")
    logger.error(f"상세 정보: {e.detail}")
    
    # 재시도 또는 대체 로직
    if e.detail.get("status") == 403:
        # 권한 부족
        raise PermissionError("Deployment 생성 권한이 없습니다")
    elif e.detail.get("status") == 422:
        # 잘못된 스펙
        raise ValueError("Deployment 스펙이 올바르지 않습니다")
    else:
        # 기타 오류는 그대로 전파
        raise
```

### 예외 정보 구조

모든 예외는 다음 정보를 포함:
- **message**: 사람이 읽을 수 있는 오류 메시지
- **status_code**: HTTP 상태 코드 (404, 409, 500 등)
- **detail**: 추가 상세 정보 (dict)
  - resource_type: 리소스 타입
  - resource_name: 리소스 이름
  - namespace: 네임스페이스 (해당하는 경우)
  - reason: Kubernetes API 오류 이유
  - api_status_code: Kubernetes API 상태 코드

---

## 테스트

각 Manager는 포괄적인 단위 테스트를 포함:

```bash
# 전체 Manager 테스트
pytest tests/infra/kubernetes/managers/ -v

# 개별 Manager 테스트
pytest tests/infra/kubernetes/managers/namespace/test_manager.py -v
pytest tests/infra/kubernetes/managers/serviceaccount/test_manager.py -v
pytest tests/infra/kubernetes/managers/role/test_manager.py -v
pytest tests/infra/kubernetes/managers/rolebinding/test_manager.py -v
# (기타 Manager들도 동일)
```

### 테스트 커버리지

| Manager | 테스트 파일 | 주요 테스트 항목 |
|---------|------------|------------------|
| NamespaceManager | test_manager.py | 초기화, CRUD, 상태 조회, 예외 처리 |
| ServiceAccountManager | test_manager.py | 초기화, CRUD, ImagePullSecret, 예외 처리 |
| RoleManager | test_manager.py | 초기화, CRUD, PolicyRule, 예외 처리 |
| RoleBindingManager | test_manager.py | 초기화, CRUD, Subject 관리, 예외 처리 |
| ConfigMapManager | (예정) | 초기화, CRUD, 데이터 업데이트, 예외 처리 |
| SecretManager | (예정) | Vault 바인딩, Injection, 예외 처리 |
| DeploymentManager | (예정) | 초기화, CRUD, 스케일링, 상태 조회, 예외 처리 |
| StatefulSetManager | (예정) | 초기화, CRUD, 스케일링, PVC, 예외 처리 |
| ServiceManager | (예정) | 초기화, CRUD, Selector 업데이트, 예외 처리 |
| PodManager | (예정) | 조회, 목록, 상태 조회, 로그, 예외 처리 |

---

## 참고 자료

- **Kubernetes 공식 문서**: https://kubernetes.io/docs/
- **RBAC 가이드**: https://kubernetes.io/docs/reference/access-authn-authz/rbac/
- **Vault Kubernetes Auth**: https://developer.hashicorp.com/vault/docs/auth/kubernetes
- **Vault Agent Injector**: https://developer.hashicorp.com/vault/docs/platform/k8s/injector
- **kubernetes-asyncio**: https://github.com/tomplus/kubernetes_asyncio
- **M-ADP 프로젝트 설계**: `/CLAUDE.md`