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
  - [PersistentVolumeClaimManager](#persistentvolumeclaimmanager)
  - [LimitRangeManager](#limitrangemanager)
  - [ResourceQuotaManager](#resourcequotamanager)
  - [DeploymentManager](#deploymentmanager)
  - [StatefulSetManager](#statefulsetmanager)
  - [DaemonSetManager](#daemonsetmanager)
  - [ReplicaSetManager](#replicasetmanager)
  - [JobManager](#jobmanager)
  - [CronJobManager](#cronjobmanager)
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

- **k8s_client**: `KubernetesClientImpl` 인스턴스 (의존성 주입)
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

### PersistentVolumeClaimManager

**경로**: `infra/kubernetes/managers/persistentvolumeclaim/manager.py`

#### 역할
Kubernetes PersistentVolumeClaim(PVC) 리소스를 관리합니다. PVC는 **영구 스토리지 요청**을 나타내며, Pod가 데이터를 영구적으로 저장할 수 있도록 합니다.

#### 주요 기능

##### 1. create_pvc()
```python
async def create_pvc(
    name: str,
    namespace: str,
    storage_size: str,
    access_modes: Optional[List[str]] = None,
    storage_class_name: Optional[str] = None,
    volume_mode: Optional[str] = None,
    selector: Optional[V1LabelSelector] = None,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None
) -> V1PersistentVolumeClaim
```

**기능**: PVC 생성
- **storage_size**: 요청할 스토리지 크기 (예: "10Gi", "500Mi")
- **access_modes**: 접근 모드 (기본값: `["ReadWriteOnce"]`)
  - `ReadWriteOnce`: 단일 노드에서 읽기/쓰기
  - `ReadOnlyMany`: 다중 노드에서 읽기 전용
  - `ReadWriteMany`: 다중 노드에서 읽기/쓰기
- **storage_class_name**: 사용할 스토리지 클래스 (동적 프로비저닝)
- **volume_mode**: `Filesystem` (기본값) 또는 `Block`

**사용 예시**:
```python
# 기본 PVC 생성 (10Gi, ReadWriteOnce)
pvc = await pvc_manager.create_pvc(
    name="data-pvc",
    namespace="student-1234",
    storage_size="10Gi"
)

# 특정 스토리지 클래스 사용
pvc = await pvc_manager.create_pvc(
    name="fast-storage",
    namespace="production",
    storage_size="100Gi",
    storage_class_name="ssd",
    access_modes=["ReadWriteOnce"]
)

# 다중 노드 읽기/쓰기 (NFS 등)
pvc = await pvc_manager.create_pvc(
    name="shared-data",
    namespace="team-workspace",
    storage_size="50Gi",
    access_modes=["ReadWriteMany"],
    storage_class_name="nfs"
)
```

##### 2. get_pvc_status()
```python
async def get_pvc_status(
    name: str,
    namespace: str
) -> Optional[Dict[str, any]]
```

**기능**: PVC 상태 조회

**반환 예시**:
```python
{
    "phase": "Bound",  # Pending, Bound, Lost
    "access_modes": ["ReadWriteOnce"],
    "capacity": {"storage": "10Gi"},
    "conditions": [
        {
            "type": "Resizing",
            "status": "False",
            "reason": "N/A",
            "message": "...",
            "last_probe_time": None,
            "last_transition_time": "2025-01-15T10:30:00Z"
        }
    ]
}
```

##### 3. resize_pvc()
```python
async def resize_pvc(
    name: str,
    namespace: str,
    new_storage_size: str
) -> V1PersistentVolumeClaim
```

**기능**: PVC 스토리지 크기 변경

**제약 사항**:
- 크기는 **증가만 가능** (축소 불가)
- StorageClass가 `allowVolumeExpansion: true` 설정 필요
- 일부 볼륨 타입은 온라인 확장 미지원 (Pod 재시작 필요)

**사용 예시**:
```python
# 10Gi → 20Gi로 확장
pvc = await pvc_manager.resize_pvc(
    name="data-pvc",
    namespace="student-1234",
    new_storage_size="20Gi"
)
```

##### 4. is_bound()
```python
async def is_bound(name: str, namespace: str) -> bool
```

**기능**: PVC가 PV에 바인딩되었는지 확인

**사용 예시**:
```python
if await pvc_manager.is_bound("data-pvc", "student-1234"):
    print("PVC가 PV에 성공적으로 바인딩되었습니다")
```

#### PVC Phase

| Phase | 의미 |
|-------|------|
| Pending | PV를 찾는 중 또는 동적 프로비저닝 대기 |
| Bound | PV에 성공적으로 바인딩됨 |
| Lost | PV를 잃어버림 (PV가 삭제됨) |

#### Access Modes 비교

| Mode | 약자 | 사용 케이스 |
|------|------|-------------|
| ReadWriteOnce | RWO | 단일 Pod 전용 스토리지 (DB, 로컬 캐시) |
| ReadOnlyMany | ROX | 여러 Pod이 읽기만 필요 (정적 자산) |
| ReadWriteMany | RWX | 여러 Pod이 동시에 쓰기 필요 (공유 파일 시스템) |

#### 특징
- **동적 프로비저닝**: StorageClass 지정 시 자동으로 PV 생성
- **정적 프로비저닝**: selector로 특정 PV 선택 가능
- **크기 확장**: resize_pvc()로 온라인 확장 (축소 불가)
- **Reclaim Policy**: PVC 삭제 시 PV 처리 방식 (Delete, Retain)

#### 사용 시나리오
- 데이터베이스 영구 저장소 (MySQL, PostgreSQL)
- StatefulSet 볼륨 (Kafka, Elasticsearch)
- 공유 파일 시스템 (팀 협업 공간)
- 로그 저장소 (장기 보관)

---

### LimitRangeManager

**경로**: `infra/kubernetes/managers/limitrange/manager.py`

#### 역할
Kubernetes LimitRange 리소스를 관리합니다. LimitRange는 **네임스페이스 내 개별 리소스(Pod, Container)의 최소/최대 제한**을 설정합니다.

#### 주요 기능

##### 1. create_limitrange()
```python
async def create_limitrange(
    name: str,
    namespace: str,
    limits: List[V1LimitRangeItem],
    labels: Optional[dict] = None,
    annotations: Optional[dict] = None
) -> V1LimitRange
```

**기능**: LimitRange 생성

**사용 예시**:
```python
from kubernetes_asyncio.client import V1LimitRangeItem

# Container CPU/Memory 제한
container_limits = V1LimitRangeItem(
    type="Container",
    max={"cpu": "2", "memory": "2Gi"},
    min={"cpu": "100m", "memory": "128Mi"},
    default={"cpu": "500m", "memory": "512Mi"},
    default_request={"cpu": "200m", "memory": "256Mi"}
)

# Pod 전체 제한
pod_limits = V1LimitRangeItem(
    type="Pod",
    max={"cpu": "4", "memory": "8Gi"},
    min={"cpu": "200m", "memory": "256Mi"}
)

# PVC 제한
pvc_limits = V1LimitRangeItem(
    type="PersistentVolumeClaim",
    max={"storage": "100Gi"},
    min={"storage": "1Gi"}
)

limitrange = await limitrange_manager.create_limitrange(
    name="student-limits",
    namespace="student-1234",
    limits=[container_limits, pod_limits, pvc_limits]
)
```

##### 2. update_limits()
```python
async def update_limits(
    name: str,
    namespace: str,
    limits: List[V1LimitRangeItem]
) -> V1LimitRange
```

**기능**: LimitRange 제한 사항 업데이트

**사용 예시**:
```python
# 제한 완화
new_limits = [
    V1LimitRangeItem(
        type="Container",
        max={"cpu": "4", "memory": "4Gi"},  # 증가
        min={"cpu": "100m", "memory": "128Mi"},
        default={"cpu": "1", "memory": "1Gi"}
    )
]

limitrange = await limitrange_manager.update_limits(
    name="student-limits",
    namespace="student-1234",
    limits=new_limits
)
```

#### LimitRange Type

| Type | 적용 대상 | 설정 가능 항목 |
|------|----------|---------------|
| Container | 개별 컨테이너 | cpu, memory, ephemeral-storage |
| Pod | Pod 전체 (모든 컨테이너 합) | cpu, memory, ephemeral-storage |
| PersistentVolumeClaim | PVC | storage |

#### LimitRange vs ResourceQuota

| 구분 | LimitRange | ResourceQuota |
|------|-----------|---------------|
| **범위** | 개별 리소스(Pod, Container) | 네임스페이스 전체 |
| **목적** | 단일 리소스 제한 | 총합 제한 |
| **강제 시점** | 리소스 생성 시 | 리소스 누적 시 |
| **예시** | "Container는 최대 2Gi 메모리" | "Namespace 전체 최대 20Gi 메모리" |

#### 특징
- **기본값 주입**: default, defaultRequest로 요청하지 않은 값 자동 설정
- **범위 제한**: min/max로 허용 범위 강제
- **비율 제한**: maxLimitRequestRatio로 limit/request 비율 제한 가능
- **즉시 적용**: 생성 시점에 검증 (기존 리소스는 영향 없음)

#### 사용 시나리오
- 학생/테넌트별 리소스 사용 제한
- 컨테이너 리소스 요청 강제 (기본값 주입)
- 과도한 리소스 요청 방지
- PVC 스토리지 크기 제한

---

### ResourceQuotaManager

**경로**: `infra/kubernetes/managers/resourcequota/manager.py`

#### 역할
Kubernetes ResourceQuota 리소스를 관리합니다. ResourceQuota는 **네임스페이스 전체의 리소스 사용량 총합**을 제한합니다.

#### 주요 기능

##### 1. create_resource_quota()
```python
async def create_resource_quota(
    name: str,
    namespace: str,
    hard_limits: Dict[str, str],
    scope_selector: Optional[Dict] = None,
    scopes: Optional[List[str]] = None,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None
) -> V1ResourceQuota
```

**기능**: ResourceQuota 생성

**사용 예시**:
```python
# 기본 리소스 제한 (Compute)
quota = await resourcequota_manager.create_resource_quota(
    name="student-quota",
    namespace="student-1234",
    hard_limits={
        # Compute 리소스
        "requests.cpu": "4",
        "requests.memory": "8Gi",
        "limits.cpu": "8",
        "limits.memory": "16Gi",
        
        # Object Count
        "pods": "50",
        "services": "10",
        "persistentvolumeclaims": "20",
        "configmaps": "50",
        "secrets": "50",
        
        # Storage
        "requests.storage": "100Gi",
    }
)

# 특정 우선순위 클래스에만 적용
quota = await resourcequota_manager.create_resource_quota(
    name="high-priority-quota",
    namespace="production",
    hard_limits={
        "pods": "20",
        "requests.cpu": "10",
        "requests.memory": "20Gi"
    },
    scopes=["PriorityClass"]
)
```

##### 2. get_quota_status()
```python
async def get_quota_status(
    name: str,
    namespace: str
) -> Optional[Dict[str, Dict[str, str]]]
```

**기능**: ResourceQuota 사용량 vs 제한 조회

**반환 예시**:
```python
{
    "hard": {
        "pods": "50",
        "requests.cpu": "4",
        "requests.memory": "8Gi"
    },
    "used": {
        "pods": "12",
        "requests.cpu": "2.5",
        "requests.memory": "3Gi"
    }
}
```

##### 3. update_resource_quota()
```python
async def update_resource_quota(
    name: str,
    namespace: str,
    hard_limits: Dict[str, str],
    scope_selector: Optional[Dict] = None,
    scopes: Optional[List[str]] = None
) -> V1ResourceQuota
```

**기능**: ResourceQuota 제한 업데이트

**사용 예시**:
```python
# 리소스 증설
quota = await resourcequota_manager.update_resource_quota(
    name="student-quota",
    namespace="student-1234",
    hard_limits={
        "requests.cpu": "8",      # 4 → 8
        "requests.memory": "16Gi", # 8Gi → 16Gi
        "pods": "100"              # 50 → 100
    }
)
```

#### ResourceQuota 리소스 종류

##### Compute Resources
| 리소스 | 의미 |
|--------|------|
| `requests.cpu` | 전체 CPU 요청 합계 |
| `requests.memory` | 전체 메모리 요청 합계 |
| `limits.cpu` | 전체 CPU 제한 합계 |
| `limits.memory` | 전체 메모리 제한 합계 |
| `requests.nvidia.com/gpu` | GPU 요청 합계 |

##### Object Count
| 리소스 | 의미 |
|--------|------|
| `pods` | Pod 개수 |
| `services` | Service 개수 |
| `services.loadbalancers` | LoadBalancer Service 개수 |
| `services.nodeports` | NodePort Service 개수 |
| `persistentvolumeclaims` | PVC 개수 |
| `configmaps` | ConfigMap 개수 |
| `secrets` | Secret 개수 |
| `replicationcontrollers` | ReplicationController 개수 |

##### Storage
| 리소스 | 의미 |
|--------|------|
| `requests.storage` | 전체 PVC 스토리지 요청 합계 |
| `persistentvolumeclaims` | PVC 개수 |
| `<storage-class-name>.storageclass.storage.k8s.io/requests.storage` | 특정 StorageClass 스토리지 합계 |
| `<storage-class-name>.storageclass.storage.k8s.io/persistentvolumeclaims` | 특정 StorageClass PVC 개수 |

#### ResourceQuota Scopes

| Scope | 적용 대상 |
|-------|----------|
| `Terminating` | activeDeadlineSeconds 설정된 Pod |
| `NotTerminating` | activeDeadlineSeconds 없는 Pod |
| `BestEffort` | requests/limits 없는 Pod |
| `NotBestEffort` | requests/limits 있는 Pod |
| `PriorityClass` | 특정 우선순위 클래스 Pod |

#### 특징
- **총합 제한**: 네임스페이스 내 모든 리소스의 합계 제한
- **생성 차단**: 할당량 초과 시 새 리소스 생성 거부
- **실시간 추적**: 리소스 생성/삭제 시 즉시 반영
- **세분화 제어**: Scope로 특정 조건의 Pod만 제한 가능

#### 사용 시나리오
- 테넌트별 전체 리소스 할당량 관리
- 비용 통제 (클라우드 환경)
- 클러스터 리소스 공정 분배
- 실수로 인한 과도한 리소스 사용 방지

#### LimitRange + ResourceQuota 조합 예시

```python
# 1. LimitRange: 개별 Pod/Container 제한
container_limits = V1LimitRangeItem(
    type="Container",
    max={"cpu": "2", "memory": "2Gi"},
    default={"cpu": "500m", "memory": "512Mi"}
)
await limitrange_manager.create_limitrange(
    name="limits",
    namespace="student-1234",
    limits=[container_limits]
)

# 2. ResourceQuota: 네임스페이스 전체 제한
await resourcequota_manager.create_resource_quota(
    name="quota",
    namespace="student-1234",
    hard_limits={
        "requests.cpu": "10",      # 전체 합계
        "requests.memory": "20Gi",
        "pods": "20"               # 최대 Pod 수
    }
)

# 결과:
# - 각 컨테이너: 최대 2 CPU, 2Gi 메모리
# - 네임스페이스: 전체 10 CPU, 20Gi 메모리, 20개 Pod
# - 예: 컨테이너당 500m CPU 기본값 → 최대 20개 Pod까지만 생성 가능
```

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

### DaemonSetManager

**경로**: `infra/kubernetes/managers/daemonset/manager.py`

#### 역할
Kubernetes DaemonSet 리소스를 관리합니다. DaemonSet은 **모든 (또는 특정) Node에서 Pod를 자동으로 실행**하는 리소스입니다.

#### Deployment와의 차이점

| 특성 | Deployment | DaemonSet |
|------|-----------|-----------|
| Pod 배치 | 여러 Node에 분산 (스케줄러가 결정) | 모든 (또는 선택한) Node에 1개씩 |
| 레플리카 수 | 명시적 지정 (replicas) | 자동 (Node 수에 따라) |
| 스케일링 | 수동 조정 가능 | Node 추가/제거 시 자동 |
| 사용 사례 | 애플리케이션 서비스 | 노드 레벨 서비스 (로깅, 모니터링) |

#### 주요 기능

##### 1. create_daemonset()
```python
async def create_daemonset(
    name: str,
    namespace: str,
    containers: List[V1Container],
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    selector_labels: Optional[Dict[str, str]] = None,
    pod_labels: Optional[Dict[str, str]] = None,
    pod_annotations: Optional[Dict[str, str]] = None
) -> V1DaemonSet
```

**기능**: DaemonSet 생성 (멱등성)
- replicas 파라미터 없음 (Node 수에 따라 자동 결정)
- 모든 Node에 자동 배포

**사용 예시**:
```python
from kubernetes_asyncio.client import V1Container, V1VolumeMount, V1Volume, V1HostPathVolumeSource

# 로그 수집 DaemonSet
daemonset = await daemonset_manager.create_daemonset(
    name="log-collector",
    namespace="kube-system",
    containers=[
        V1Container(
            name="fluentd",
            image="fluent/fluentd:latest",
            volume_mounts=[
                V1VolumeMount(
                    name="varlog",
                    mount_path="/var/log",
                    read_only=True
                ),
                V1VolumeMount(
                    name="varlibdockercontainers",
                    mount_path="/var/lib/docker/containers",
                    read_only=True
                )
            ]
        )
    ],
    labels={"app": "log-collector"},
    # Pod Template에 볼륨 추가
    pod_spec_volumes=[
        V1Volume(
            name="varlog",
            host_path=V1HostPathVolumeSource(path="/var/log")
        ),
        V1Volume(
            name="varlibdockercontainers",
            host_path=V1HostPathVolumeSource(path="/var/lib/docker/containers")
        )
    ]
)
```

##### 2. get_daemonset_status()
```python
async def get_daemonset_status(
    name: str,
    namespace: str
) -> Optional[Dict[str, any]]
```

**기능**: DaemonSet 상태 조회

**반환 예시**:
```python
{
    "current_number_scheduled": 5,   # 현재 실행 중인 Pod 수
    "desired_number_scheduled": 5,   # 목표 Pod 수 (Node 수)
    "number_available": 5,           # 사용 가능한 Pod 수
    "number_ready": 5,               # 준비된 Pod 수
    "number_misscheduled": 0,        # 잘못 스케줄된 Pod 수
    "number_unavailable": 0,         # 사용 불가능한 Pod 수
    "updated_number_scheduled": 5,   # 업데이트된 Pod 수
    "conditions": [
        {
            "type": "Available",
            "status": "True",
            "reason": "MinimumAvailable",
            "message": "DaemonSet has minimum availability."
        }
    ]
}
```

##### 3. update_labels()
```python
async def update_labels(
    name: str,
    namespace: str,
    labels: Dict[str, str],
    merge: bool = True
) -> V1DaemonSet
```

**기능**: DaemonSet 레이블 업데이트
- merge=True: 기존 레이블과 병합
- merge=False: 기존 레이블 전체 교체

#### Node Selector를 사용한 선택적 배포

DaemonSet을 특정 Node에만 배포하려면 nodeSelector 사용:

```python
daemonset = await daemonset_manager.create_daemonset(
    name="nvidia-driver",
    namespace="kube-system",
    containers=[...],
    node_selector={"gpu": "nvidia"}  # gpu=nvidia 레이블이 있는 Node에만 배포
)
```

#### 특징
- **자동 스케일링**: Node 추가 시 자동으로 Pod 생성
- **Node 레벨 서비스**: 모든 Node에서 실행되어야 하는 서비스에 적합
- **Rolling Update**: 순차적 업데이트 지원
- **Host 리소스 접근**: hostPath, hostNetwork 등으로 Node 리소스 접근 가능

#### 사용 시나리오
- **로그 수집**: Fluentd, Filebeat (각 Node의 로그 수집)
- **모니터링 에이전트**: Prometheus Node Exporter, Datadog Agent
- **네트워크 플러그인**: CNI 플러그인 (Calico, Flannel)
- **스토리지 플러그인**: CSI 드라이버
- **보안 에이전트**: 침입 탐지 시스템 (Falco)

---

### ReplicaSetManager

**경로**: `infra/kubernetes/managers/replicaset/manager.py`

#### 역할
Kubernetes ReplicaSet 리소스를 관리합니다. ReplicaSet은 **지정된 수의 Pod 레플리카를 유지**하는 리소스입니다.

**중요**: 일반적으로 ReplicaSet을 **직접 생성하지 않습니다**. Deployment가 내부적으로 ReplicaSet을 관리합니다.

#### Deployment와의 관계

```
Deployment (상위 컨트롤러)
  └── ReplicaSet (중간 컨트롤러, 버전별로 생성)
        └── Pod (실제 워크로드)
```

- **Deployment**: 롤아웃, 롤백, 업데이트 전략 관리
- **ReplicaSet**: 특정 버전의 Pod 레플리카 수 관리
- **Pod**: 실제 컨테이너 실행

#### 언제 직접 사용하는가?

ReplicaSet을 직접 사용하는 경우는 매우 드물지만, 다음 시나리오에서 필요할 수 있습니다:
- 단순 레플리카 관리만 필요하고 롤아웃 기능이 불필요한 경우
- 레거시 애플리케이션 호환성
- 매우 세밀한 ReplicaSet 제어가 필요한 경우

**권장**: 대부분의 경우 **Deployment를 사용**하는 것이 좋습니다.

#### 주요 기능

##### 1. create_replicaset()
```python
async def create_replicaset(
    name: str,
    namespace: str,
    containers: List[V1Container],
    replicas: int = 1,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    selector_labels: Optional[Dict[str, str]] = None,
    pod_labels: Optional[Dict[str, str]] = None,
    pod_annotations: Optional[Dict[str, str]] = None
) -> V1ReplicaSet
```

**기능**: ReplicaSet 생성 (멱등성)
- Deployment와 거의 동일한 파라미터
- 직접 생성은 권장하지 않음

**사용 예시**:
```python
# 일반적으로 직접 생성하지 않지만, 필요한 경우:
replicaset = await replicaset_manager.create_replicaset(
    name="myapp-rs",
    namespace="student-1234",
    replicas=3,
    containers=[
        V1Container(
            name="app",
            image="myapp:v1.0.0"
        )
    ],
    labels={"app": "myapp", "version": "v1"}
)
```

##### 2. update_replicas()
```python
async def update_replicas(
    name: str,
    namespace: str,
    replicas: int
) -> V1ReplicaSet
```

**기능**: 레플리카 수 변경 (스케일링)

**사용 예시**:
```python
# 스케일 아웃
await replicaset_manager.update_replicas("myapp-rs", "student-1234", replicas=5)
```

##### 3. get_replicaset_status()
```python
async def get_replicaset_status(
    name: str,
    namespace: str
) -> Optional[Dict[str, any]]
```

**기능**: ReplicaSet 상태 조회

**반환 예시**:
```python
{
    "replicas": 3,              # 전체 레플리카 수
    "ready_replicas": 3,        # 준비된 레플리카 수
    "available_replicas": 3,    # 사용 가능한 레플리카 수
    "fully_labeled_replicas": 3,# 레이블이 완전한 레플리카 수
    "conditions": [
        {
            "type": "ReplicaFailure",
            "status": "False",
            "reason": "NoFailure",
            "message": "All replicas are running"
        }
    ]
}
```

#### Deployment가 ReplicaSet을 관리하는 방식

```python
# Deployment 생성 시
deployment = await deployment_manager.create_deployment(
    name="myapp",
    namespace="student-1234",
    replicas=3,
    containers=[V1Container(name="app", image="myapp:v1.0.0")]
)
# Deployment가 자동으로 myapp-xxxxx ReplicaSet 생성

# 이미지 업데이트 시
# 1. Deployment가 새로운 ReplicaSet 생성 (myapp-yyyyy)
# 2. 새 ReplicaSet의 레플리카 수를 점진적으로 증가
# 3. 기존 ReplicaSet의 레플리카 수를 점진적으로 감소
# 4. 롤아웃 완료 후 기존 ReplicaSet은 0개 유지 (롤백 대비)
```

#### 특징
- **레플리카 보장**: 지정된 수의 Pod를 항상 유지
- **자동 복구**: Pod 장애 시 자동으로 새 Pod 생성
- **레이블 Selector**: matchLabels로 관리할 Pod 식별
- **Deployment보다 단순**: 롤아웃 전략 없음

#### Deployment와 ReplicaSet의 선택

| 기능 | Deployment | ReplicaSet |
|------|-----------|-----------|
| 롤링 업데이트 | ✅ 지원 | ❌ 미지원 |
| 롤백 | ✅ 지원 | ❌ 미지원 |
| 업데이트 전략 | RollingUpdate, Recreate | - |
| ReplicaSet 관리 | 자동 (내부적으로 생성) | 수동 |
| 권장 사용 | ✅ 대부분의 경우 | ⚠️ 특수한 경우만 |

**결론**: 특별한 이유가 없다면 **Deployment를 사용**하세요.

---

### JobManager

**경로**: `infra/kubernetes/managers/job/manager.py`

#### 역할
Kubernetes Job 리소스를 관리합니다. Job은 **한 번 실행하고 완료되는 작업(batch processing)**을 관리하는 리소스입니다.

#### Deployment와의 차이점

| 특성 | Deployment | Job |
|------|-----------|-----|
| 목적 | 장기 실행 서비스 | 일회성 작업 |
| 완료 개념 | 없음 (계속 실행) | 있음 (성공 완료 후 종료) |
| 재시작 | Pod 실패 시 항상 재시작 | backoffLimit까지만 재시도 |
| 스케일링 | replicas로 지정 | completions와 parallelism으로 제어 |
| 사용 사례 | 웹 서버, API 서버 | 데이터 처리, 백업, 마이그레이션 |

#### 주요 기능

##### 1. create_job()
```python
async def create_job(
    name: str,
    namespace: str,
    containers: List[V1Container],
    completions: Optional[int] = None,
    parallelism: Optional[int] = None,
    backoff_limit: Optional[int] = None,
    active_deadline_seconds: Optional[int] = None,
    ttl_seconds_after_finished: Optional[int] = None,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    pod_labels: Optional[Dict[str, str]] = None,
    pod_annotations: Optional[Dict[str, str]] = None,
    restart_policy: str = "Never"
) -> V1Job
```

**기능**: Job 생성 (멱등성)

**주요 파라미터**:
- **completions**: 성공적으로 완료해야 할 Pod 수 (기본값: 1)
- **parallelism**: 동시에 실행할 수 있는 최대 Pod 수 (기본값: 1)
- **backoff_limit**: 실패 시 재시도 횟수 (기본값: 6)
- **active_deadline_seconds**: Job의 최대 실행 시간 (초)
- **ttl_seconds_after_finished**: 완료 후 자동 삭제까지의 시간 (초)
- **restart_policy**: Pod 재시작 정책 ("Never" 또는 "OnFailure")

**사용 예시**:

**단순 일회성 작업**:
```python
from kubernetes_asyncio.client import V1Container, V1EnvVar

# 데이터베이스 백업 Job
job = await job_manager.create_job(
    name="db-backup",
    namespace="production",
    containers=[
        V1Container(
            name="backup",
            image="mysql:8.0",
            command=["mysqldump"],
            args=[
                "-h", "mysql.default.svc.cluster.local",
                "-u", "root",
                "--all-databases"
            ]
        )
    ],
    completions=1,
    backoff_limit=3,
    ttl_seconds_after_finished=3600,  # 1시간 후 자동 삭제
    restart_policy="OnFailure"
)
```

**병렬 처리 작업**:
```python
# 10개의 작업을 3개씩 병렬로 처리
job = await job_manager.create_job(
    name="data-processing",
    namespace="analytics",
    containers=[
        V1Container(
            name="processor",
            image="data-processor:latest",
            command=["python", "process.py"]
        )
    ],
    completions=10,      # 총 10번 성공적으로 완료
    parallelism=3,       # 동시에 최대 3개 Pod 실행
    backoff_limit=5,
    active_deadline_seconds=3600,  # 최대 1시간 내에 완료
    ttl_seconds_after_finished=86400  # 24시간 후 삭제
)
```

**제한 시간이 있는 작업**:
```python
# 최대 30분 내에 완료되어야 하는 마이그레이션
job = await job_manager.create_job(
    name="db-migration",
    namespace="production",
    containers=[
        V1Container(
            name="migrate",
            image="migrate:latest",
            command=["./migrate", "up"]
        )
    ],
    active_deadline_seconds=1800,  # 30분
    backoff_limit=0,  # 재시도 없음 (한 번만 실행)
    ttl_seconds_after_finished=7200  # 2시간 후 삭제
)
```

##### 2. get_job_status()
```python
async def get_job_status(
    name: str,
    namespace: str
) -> Optional[Dict[str, any]]
```

**기능**: Job 상태 조회

**반환 예시**:
```python
{
    "active": 2,           # 현재 실행 중인 Pod 수
    "succeeded": 3,        # 성공한 Pod 수
    "failed": 1,           # 실패한 Pod 수
    "start_time": "2025-01-15T10:00:00Z",
    "completion_time": None,  # 완료되지 않았으면 None
    "conditions": [
        {
            "type": "Complete",
            "status": "False",
            "reason": "JobRunning",
            "message": "Job is still running"
        }
    ]
}
```

##### 3. is_completed()
```python
async def is_completed(
    name: str,
    namespace: str
) -> bool
```

**기능**: Job 완료 여부 확인

**사용 예시**:
```python
# Job 완료 대기
import asyncio

while not await job_manager.is_completed("db-backup", "production"):
    await asyncio.sleep(5)

print("백업 완료!")
```

#### Job 패턴

##### 패턴 1: 단일 작업 (Single Job)
```python
completions=1, parallelism=1
```
- 하나의 Pod가 실행되어 작업 완료
- 실패 시 backoffLimit까지 재시도

##### 패턴 2: 고정 완료 횟수 (Fixed Completion Count)
```python
completions=10, parallelism=3
```
- 총 10번 성공적으로 완료
- 동시에 최대 3개 Pod 실행
- 큐에서 작업을 가져오는 경우에 유용

##### 패턴 3: 작업 큐 패턴 (Work Queue)
```python
completions=None, parallelism=5
```
- completions 미지정
- Pod가 작업 큐에서 작업을 가져와 처리
- 큐가 비면 Pod가 자동 종료

#### Restart Policy

| 정책 | 동작 | 사용 시나리오 |
|------|------|---------------|
| **Never** | 실패 시 Pod를 재시작하지 않음 | 재시도가 의미 없는 작업 |
| **OnFailure** | 실패 시 같은 Pod를 재시작 | 일시적 오류로 인한 실패 가능성 |

#### 특징
- **완료 보장**: completions만큼 성공적으로 완료
- **병렬 처리**: parallelism으로 동시 실행 제어
- **재시도 제한**: backoffLimit로 무한 재시도 방지
- **자동 정리**: ttlSecondsAfterFinished로 완료된 Job 자동 삭제
- **타임아웃**: activeDeadlineSeconds로 실행 시간 제한

#### 사용 시나리오
- **데이터 처리**: 배치 처리, ETL 작업
- **백업/복원**: 데이터베이스 백업, 파일 백업
- **마이그레이션**: 스키마 마이그레이션, 데이터 이전
- **리포트 생성**: 일일/주간 리포트
- **미디어 처리**: 이미지/비디오 변환, 썸네일 생성

---

### CronJobManager

**경로**: `infra/kubernetes/managers/cronjob/manager.py`

#### 역할
Kubernetes CronJob 리소스를 관리합니다. CronJob은 **정해진 스케줄에 따라 주기적으로 Job을 실행**하는 리소스입니다.

#### Job과의 관계

```
CronJob (스케줄러)
  └── Job (작업 실행 단위, CronJob이 스케줄에 따라 생성)
        └── Pod (실제 워크로드)
```

- **CronJob**: 스케줄 정의 및 Job 생성 관리
- **Job**: 각 스케줄 시점에 생성되어 작업 실행
- **Pod**: Job이 관리하는 실제 컨테이너

#### 주요 기능

##### 1. create_cronjob()
```python
async def create_cronjob(
    name: str,
    namespace: str,
    schedule: str,
    containers: List[V1Container],
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    suspend: bool = False,
    concurrency_policy: str = "Allow",
    successful_jobs_history_limit: Optional[int] = 3,
    failed_jobs_history_limit: Optional[int] = 1,
    starting_deadline_seconds: Optional[int] = None,
    restart_policy: str = "OnFailure"
) -> V1CronJob
```

**기능**: CronJob 생성 (멱등성)

**주요 파라미터**:
- **schedule**: Cron 표현식 (예: "0 */2 * * *")
- **suspend**: CronJob 일시 중지 여부 (기본값: False)
- **concurrency_policy**: 동시 실행 정책 (Allow, Forbid, Replace)
- **successful_jobs_history_limit**: 성공한 Job 보관 개수 (기본값: 3)
- **failed_jobs_history_limit**: 실패한 Job 보관 개수 (기본값: 1)
- **starting_deadline_seconds**: Job 시작 데드라인 (초)
- **restart_policy**: Pod 재시작 정책 (OnFailure, Never)

**사용 예시**:

**데이터베이스 백업 (매일 새벽 2시)**:
```python
from kubernetes_asyncio.client import V1Container

cronjob = await cronjob_manager.create_cronjob(
    name="daily-backup",
    namespace="production",
    schedule="0 2 * * *",  # 매일 02:00
    containers=[
        V1Container(
            name="backup",
            image="mysql:8.0",
            command=["sh", "-c"],
            args=[
                "mysqldump -h $DB_HOST -u $DB_USER --all-databases > /backup/$(date +%Y%m%d).sql"
            ]
        )
    ],
    concurrency_policy="Forbid",  # 이전 백업이 진행 중이면 건너뜀
    successful_jobs_history_limit=7,  # 최근 7일간의 성공한 Job 보관
    failed_jobs_history_limit=3,
    restart_policy="OnFailure"
)
```

**로그 정리 (매주 일요일 자정)**:
```python
cronjob = await cronjob_manager.create_cronjob(
    name="weekly-log-cleanup",
    namespace="logging",
    schedule="0 0 * * 0",  # 매주 일요일 00:00
    containers=[
        V1Container(
            name="cleanup",
            image="busybox:latest",
            command=["sh", "-c"],
            args=[
                "find /logs -name '*.log' -mtime +30 -delete"
            ]
        )
    ],
    concurrency_policy="Replace",  # 이전 작업을 중단하고 새 작업 시작
    successful_jobs_history_limit=4,  # 최근 4주 보관
    failed_jobs_history_limit=2
)
```

**리포트 생성 (매시간)**:
```python
cronjob = await cronjob_manager.create_cronjob(
    name="hourly-report",
    namespace="analytics",
    schedule="0 * * * *",  # 매시간 정각
    containers=[
        V1Container(
            name="report-generator",
            image="report-gen:latest",
            command=["python", "generate_report.py"]
        )
    ],
    concurrency_policy="Allow",  # 동시 실행 허용
    successful_jobs_history_limit=24,  # 최근 24시간 보관
    starting_deadline_seconds=300  # 5분 내에 시작하지 못하면 건너뜀
)
```

**일시 중지된 CronJob**:
```python
# 나중에 활성화할 CronJob 미리 생성
cronjob = await cronjob_manager.create_cronjob(
    name="scheduled-maintenance",
    namespace="production",
    schedule="0 3 * * 6",  # 매주 토요일 03:00
    containers=[...],
    suspend=True  # 일시 중지 상태로 생성
)

# 필요할 때 활성화
await cronjob_manager.resume_cronjob("scheduled-maintenance", "production")
```

##### 2. Cron 스케줄 표현식

Cron 표현식: `분 시 일 월 요일`

```
┌───────────── 분 (0 - 59)
│ ┌───────────── 시 (0 - 23)
│ │ ┌───────────── 일 (1 - 31)
│ │ │ ┌───────────── 월 (1 - 12)
│ │ │ │ ┌───────────── 요일 (0 - 6, 0=일요일)
│ │ │ │ │
* * * * *
```

**주요 예시**:
```python
"0 2 * * *"       # 매일 02:00
"*/15 * * * *"    # 15분마다
"0 */2 * * *"     # 2시간마다
"0 9-17 * * 1-5"  # 평일 9시~17시 매시간
"0 0 1 * *"       # 매월 1일 자정
"0 0 * * 0"       # 매주 일요일 자정
"30 3 * * 1"      # 매주 월요일 03:30
```

##### 3. Concurrency Policy (동시 실행 정책)

| 정책 | 동작 | 사용 시나리오 |
|------|------|---------------|
| **Allow** | 이전 Job이 실행 중이어도 새 Job 생성 | 동시 실행이 안전한 작업 |
| **Forbid** | 이전 Job이 실행 중이면 새 Job 건너뜀 | 동시 실행 불가능한 작업 (백업 등) |
| **Replace** | 이전 Job을 중단하고 새 Job 시작 | 최신 데이터만 중요한 작업 |

**예시**:
```python
# Allow: 데이터 수집 (동시 실행 가능)
concurrency_policy="Allow"

# Forbid: 데이터베이스 백업 (동시 실행 불가)
concurrency_policy="Forbid"

# Replace: 캐시 갱신 (최신 것만 필요)
concurrency_policy="Replace"
```

##### 4. suspend_cronjob() / resume_cronjob()
```python
async def suspend_cronjob(
    name: str,
    namespace: str
) -> V1CronJob

async def resume_cronjob(
    name: str,
    namespace: str
) -> V1CronJob
```

**기능**: CronJob 일시 중지/재개

**사용 예시**:
```python
# 유지보수 기간 동안 백업 중지
await cronjob_manager.suspend_cronjob("daily-backup", "production")

# 유지보수 완료 후 재개
await cronjob_manager.resume_cronjob("daily-backup", "production")
```

##### 5. get_cronjob_status()
```python
async def get_cronjob_status(
    name: str,
    namespace: str
) -> Optional[Dict[str, any]]
```

**기능**: CronJob 상태 조회

**반환 예시**:
```python
{
    "last_schedule_time": "2025-01-15T02:00:00Z",
    "last_successful_time": "2025-01-15T02:05:00Z",
    "active": [
        {"name": "daily-backup-28421650", "namespace": "production"}
    ]
}
```

#### 특징
- **자동 스케줄링**: Cron 표현식으로 정확한 시간에 실행
- **이력 관리**: 성공/실패한 Job 이력 자동 관리
- **동시 실행 제어**: concurrencyPolicy로 동시 실행 제어
- **일시 중지**: suspend로 스케줄 일시 중지 가능
- **타임존**: Kubernetes 1.27+부터 timeZone 필드 지원

#### 사용 시나리오
- **정기 백업**: 데이터베이스, 파일 시스템 백업
- **데이터 동기화**: 외부 시스템과 데이터 동기화
- **정기 리포트**: 일일/주간/월간 리포트 생성
- **정리 작업**: 오래된 로그/파일 삭제
- **헬스 체크**: 주기적인 시스템 점검
- **캐시 갱신**: 정기적인 캐시 데이터 갱신

#### CronJob vs Job 선택

| 사용 사례 | 선택 |
|-----------|------|
| 정기적으로 실행해야 하는 작업 | CronJob |
| 한 번만 실행하면 되는 작업 | Job |
| 특정 이벤트에 반응하는 작업 | Job (이벤트 트리거) |
| 스케줄링이 필요한 작업 | CronJob |

---

### PodManager

**경로**: `infra/kubernetes/managers/pod/manager.py`

#### 역할
Kubernetes Pod 리소스를 생성/조회/삭제 및 관찰하는 클래스입니다.

#### 설계 의도

Pod를 직접 생성할 수 있으나:
- ⚠️ Pod 장애 시 자동 복구 없음
- ⚠️ 롤링 업데이트 불가능
- ⚠️ 스케일링 불가능
- ⚠️ 선언적 관리 불가능

운영 환경에서는 Deployment/StatefulSet 등 컨트롤러 기반 사용을 권장합니다.

#### 주요 기능

##### 1. create_pod()
```python
async def create_pod(
    name: str,
    namespace: str,
    containers: List[V1Container],
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    restart_policy: str = "Always",
    service_account_name: Optional[str] = None
) -> V1Pod
```

**기능**: Pod 생성 (멱등성 보장)

**사용 예시**:
```python
from kubernetes_asyncio.client import V1Container

pod = await pod_manager.create_pod(
    name="debug-pod",
    namespace="student-1234",
    containers=[V1Container(name="debug", image="busybox")],
    restart_policy="Never"
)
```

##### 2. get_pod()
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

##### 3. delete_pod()
```python
async def delete_pod(
    name: str,
    namespace: str,
    grace_period_seconds: Optional[int] = None
) -> bool
```

**기능**: Pod 삭제

**사용 예시**:
```python
await pod_manager.delete_pod("debug-pod", "student-1234")
```

##### 4. list_pods()
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

##### 5. get_pod_status()
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

##### 6. get_pod_logs()
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

##### 7. list_pods_by_owner()
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
- **생성/삭제 지원**: 단일 Pod 생성/삭제 가능
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
    │   ├── PersistentVolumeClaimCreationException
    │   ├── LimitRangeCreationException
    │   ├── ResourceQuotaCreationException
    │   ├── DeploymentCreationException
    │   ├── StatefulSetCreationException
    │   ├── DaemonSetCreationException
    │   ├── ReplicaSetCreationException
    │   ├── JobCreationException
    │   ├── CronJobCreationException
    │   └── ServiceCreationException
    ├── ResourceReadException
    │   ├── NamespaceReadException
    │   ├── ServiceAccountReadException
    │   ├── RoleReadException
    │   ├── RoleBindingReadException
    │   ├── ConfigMapReadException
    │   ├── PersistentVolumeClaimReadException
    │   ├── LimitRangeReadException
    │   ├── ResourceQuotaReadException
    │   ├── DeploymentReadException
    │   ├── StatefulSetReadException
    │   ├── DaemonSetReadException
    │   ├── ReplicaSetReadException
    │   ├── JobReadException
    │   ├── CronJobReadException
    │   ├── ServiceReadException
    │   └── PodReadException
    ├── ResourceUpdateException
    │   ├── NamespaceUpdateException
    │   ├── ServiceAccountUpdateException
    │   ├── RoleUpdateException
    │   ├── RoleBindingUpdateException
    │   ├── ConfigMapUpdateException
    │   ├── PersistentVolumeClaimUpdateException
    │   ├── LimitRangeUpdateException
    │   ├── ResourceQuotaUpdateException
    │   ├── DeploymentUpdateException
    │   ├── StatefulSetUpdateException
    │   ├── DaemonSetUpdateException
    │   ├── ReplicaSetUpdateException
    │   ├── JobUpdateException
    │   ├── CronJobUpdateException
    │   └── ServiceUpdateException
    ├── ResourceDeletionException
    │   ├── NamespaceDeletionException
    │   ├── ServiceAccountDeletionException
    │   ├── RoleDeletionException
    │   ├── RoleBindingDeletionException
    │   ├── ConfigMapDeletionException
    │   ├── PersistentVolumeClaimDeletionException
    │   ├── LimitRangeDeletionException
    │   ├── ResourceQuotaDeletionException
    │   ├── DeploymentDeletionException
    │   ├── StatefulSetDeletionException
    │   ├── DaemonSetDeletionException
    │   ├── ReplicaSetDeletionException
    │   ├── JobDeletionException
    │   ├── CronJobDeletionException
    │   └── ServiceDeletionException
    ├── ResourceListException
    │   ├── NamespaceListException
    │   ├── ServiceAccountListException
    │   ├── RoleListException
    │   ├── RoleBindingListException
    │   ├── ConfigMapListException
    │   ├── PersistentVolumeClaimListException
    │   ├── LimitRangeListException
    │   ├── ResourceQuotaListException
    │   ├── DeploymentListException
    │   ├── StatefulSetListException
    │   ├── DaemonSetListException
    │   ├── ReplicaSetListException
    │   ├── JobListException
    │   ├── CronJobListException
    │   ├── ServiceListException
    │   └── PodListException
    └── VaultException (infra/kubernetes/managers/secret/exceptions.py)
        ├── SecretAccessBindingException
        ├── SecretAccessUnbindingException
        └── VaultInjectionException
```

### 예외 처리 예시

```python
from src.infra.kubernetes.managers.deployment import (
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
| ConfigMapManager | test_manager.py | 초기화, CRUD, 데이터 업데이트, 예외 처리 |
| SecretManager | test_manager.py | Vault 바인딩, Injection, 예외 처리 |
| PersistentVolumeClaimManager | test_manager.py | 초기화, CRUD, 크기 조정, 상태 조회, 예외 처리 |
| LimitRangeManager | test_manager.py | 초기화, CRUD, 제한 업데이트, 예외 처리 |
| ResourceQuotaManager | test_manager.py | 초기화, CRUD, 할당량 업데이트, 상태 조회, 예외 처리 |
| DeploymentManager | test_manager.py | 초기화, CRUD, 스케일링, 상태 조회, 예외 처리 |
| StatefulSetManager | test_manager.py | 초기화, CRUD, 스케일링, PVC, 예외 처리 |
| DaemonSetManager | test_manager.py | 초기화, CRUD, 상태 조회, 예외 처리 |
| ReplicaSetManager | test_manager.py | 초기화, CRUD, 스케일링, 상태 조회, 예외 처리 |
| JobManager | test_manager.py | 초기화, CRUD, 상태 조회, 완료 확인, 예외 처리 |
| CronJobManager | test_manager.py | 초기화, CRUD, Suspend/Resume, 예외 처리 |
| ServiceManager | test_manager.py | 초기화, CRUD, Selector 업데이트, 예외 처리 |
| PodManager | test_manager.py | 조회, 목록, 상태 조회, 로그, 예외 처리 |

---

## 참고 자료

- **Kubernetes 공식 문서**: https://kubernetes.io/docs/
- **RBAC 가이드**: https://kubernetes.io/docs/reference/access-authn-authz/rbac/
- **Vault Kubernetes Auth**: https://developer.hashicorp.com/vault/docs/auth/kubernetes
- **Vault Agent Injector**: https://developer.hashicorp.com/vault/docs/platform/k8s/injector
- **kubernetes-asyncio**: https://github.com/tomplus/kubernetes_asyncio
- **M-ADP 프로젝트 설계**: `/CLAUDE.md`
