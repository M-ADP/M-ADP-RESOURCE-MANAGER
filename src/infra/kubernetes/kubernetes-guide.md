# Kubernetes Client 가이드

M-ADP Resource Manager Server의 Kubernetes Client 설정 및 사용 가이드입니다.

## 목차
- [개요](#개요)
- [역할과 책임](#역할과-책임)
- [설정 방법](#설정-방법)
- [설정 시 유의사항](#설정-시-유의사항)
- [사용 패턴](#사용-패턴)
- [예외 처리](#예외-처리)
- [모범 사례](#모범-사례)

---

## 개요

`KubernetesClientImpl`는 M-ADP Resource Manager Server가 Kubernetes API와 통신하기 위한 **비동기 클라이언트 래퍼 클래스**입니다. 

### 기술 스택
- **라이브러리**: `kubernetes-asyncio` (공식 Kubernetes Python 클라이언트의 비동기 버전)
- **패턴**: 싱글톤 패턴 (애플리케이션 전체에서 하나의 인스턴스만 사용)
- **API 스타일**: async/await (FastAPI와의 통합을 위한 비동기 처리)

---

## 역할과 책임

### 1. Kubernetes API 연결 관리

KubernetesClient는 Kubernetes 클러스터와의 **안정적이고 효율적인 연결**을 책임집니다.

#### 주요 역할
- ✅ Kubernetes 설정 로드 (kubeconfig 또는 in-cluster config)
- ✅ API 서버 연결 초기화
- ✅ API 클라이언트 인스턴스 생성 및 관리
- ✅ 연결 리소스 정리 (graceful shutdown)

#### 책임 범위
```
┌─────────────────────────────────────────────┐
│         KubernetesClientImpl                    │
├─────────────────────────────────────────────┤
│ • 설정 로드 (kubeconfig / in-cluster)       │
│ • API 클라이언트 초기화                     │
│ • 연결 상태 관리                            │
│ • 리소스 정리                               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│      Kubernetes API Clients                 │
├─────────────────────────────────────────────┤
│ • CoreV1Api    (Pod, Service, Namespace 등)│
│ • AppsV1Api    (Deployment, StatefulSet 등)│
│ • RbacV1Api    (Role, RoleBinding 등)      │
│ • BatchV1Api   (Job, CronJob)              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Resource Managers                   │
├─────────────────────────────────────────────┤
│ • NamespaceManager                          │
│ • ServiceAccountManager                     │
│ • RoleManager                               │
│ • DeploymentManager                         │
│ • ...                                       │
└─────────────────────────────────────────────┘
```

### 2. API 클라이언트 제공

KubernetesClient는 다음 4가지 API 클라이언트를 제공합니다:

| API 클라이언트 | 관리 리소스 | 사용 Manager                                                                                           |
|---------------|------------|------------------------------------------------------------------------------------------------------|
| `core_v1` | Namespace, ServiceAccount, Pod, Service, ConfigMap, Secret, PersistentVolumeClaim, ResourceQuota, LimitRange | NamespaceManager, ServiceAccountManager, PodManager, ServiceManager, ConfigMapManager, SecretManager, PersistentVolumeClaimManager, ResourceQuotaManager, LimitRangeManager |
| `apps_v1` | Deployment, StatefulSet, DaemonSet, ReplicaSet | DeploymentManager, StatefulSetManager, DaemonSetManager, ReplicaSetManager                           |
| `rbac_v1` | Role, RoleBinding, ClusterRole, ClusterRoleBinding | RoleManager, RoleBindingManager                                                                      |
| `batch_v1` | Job, CronJob | JobManager, CronJobManager                                                                           | `apps_v1` | Deployment, StatefulSet, DaemonSet, ReplicaSet | DeploymentManager, StatefulSetManager, ReplicaSetManager, DaemonSetManager                           |
| `rbac_v1` | Role, RoleBinding, ClusterRole, ClusterRoleBinding | RoleManager, RoleBindingManager                                                                      |
| `batch_v1` | Job, CronJob | JobManager, CronJobManager                                                                           |

### 3. 설정 추상화

KubernetesClient는 복잡한 Kubernetes 연결 설정을 **단순한 설정 객체**로 추상화합니다.

#### 지원하는 연결 방식
1. **기본 kubeconfig** (`~/.kube/config`)
2. **사용자 지정 kubeconfig** (파일 경로 지정)
3. **In-cluster 설정** (Pod 내부에서 실행 시)
4. **직접 API 서버 URL** (개발/테스트 환경)

---

## 설정 방법

### 1. 환경 변수를 통한 설정

KubernetesConfig는 환경 변수를 통해 설정할 수 있습니다. 모든 환경 변수는 `K8S_` 접두사를 사용합니다.

```bash
# kubeconfig 파일 경로 지정
export K8S_KUBECONFIG_PATH="/path/to/kubeconfig"

# In-cluster 설정 사용 (Pod 내부 실행 시)
export K8S_USE_IN_CLUSTER_CONFIG=true

# API 서버 URL 직접 지정
export K8S_API_SERVER_URL="https://kubernetes.default.svc"

# 기본 네임스페이스 설정
export K8S_DEFAULT_NAMESPACE="default"

# API 타임아웃 (초)
export K8S_API_TIMEOUT=60

# 재시도 횟수
export K8S_MAX_RETRIES=3
```

### 2. 설정 객체를 통한 직접 설정

```python
from src.common.config.kubernetes import KubernetesConfig
from src.infra.kubernetes.client import KubernetesClientImpl
from src.core import get_logger

# 설정 객체 생성
k8s_config = KubernetesConfig(
    kubeconfig_path="/path/to/kubeconfig",
    default_namespace="madp-system",
    api_timeout=120
)

# 클라이언트 초기화
logger = get_logger()
k8s_client = KubernetesClientImpl(k8s_config, logger)
await k8s_client.initialize()
```

### 3. 의존성 주입을 통한 사용 (권장)

FastAPI 의존성 주입 패턴 활용:

```python
from src.infra.kubernetes.client import get_kubernetes_client


# FastAPI 라우트에서 사용
@router.get("/namespaces")
async def list_namespaces(
        k8s_client: KubernetesClientImpl = Depends(get_kubernetes_client)
):
    """Namespace 목록 조회"""
    namespaces = await k8s_client.core_v1.list_namespace()
    return namespaces.items
```

---

## 설정 시 유의사항

### 1. 연결 방식 선택 기준

#### 📌 개발 환경 (로컬)
```bash
# 기본 kubeconfig 사용 (권장)
# 별도 설정 없이 ~/.kube/config 자동 로드

# 또는 특정 kubeconfig 파일 지정
export K8S_KUBECONFIG_PATH="$HOME/.kube/config-dev"
```

**장점**:
- kubectl과 동일한 설정 사용
- 컨텍스트 전환 가능 (`kubectl config use-context`)

**유의사항**:
- ⚠️ kubeconfig 파일의 권한이 적절한지 확인 (600 또는 400)
- ⚠️ 만료된 인증서나 토큰이 없는지 확인

#### 📌 스테이징/프로덕션 환경 (Kubernetes Pod 내부)
```bash
# In-cluster 설정 사용 (필수)
export K8S_USE_IN_CLUSTER_CONFIG=true
```

**장점**:
- ServiceAccount 기반 자동 인증
- 클러스터 내부 DNS 사용 (빠른 연결)
- 토큰 자동 갱신

**유의사항**:
- ⚠️ Pod의 ServiceAccount에 적절한 RBAC 권한이 있는지 확인
- ⚠️ ServiceAccount Token이 자동 마운트되는지 확인 (`automountServiceAccountToken: true`)

#### 📌 CI/CD 또는 외부 서버
```bash
# 사용자 지정 kubeconfig 파일 사용
export K8S_KUBECONFIG_PATH="/var/secrets/kubeconfig"
```

**유의사항**:
- ⚠️ kubeconfig 파일을 안전하게 저장 (Secret Management)
- ⚠️ 최소 권한 원칙 적용 (필요한 네임스페이스만 접근)

### 2. RBAC 권한 설정

KubernetesClient가 정상 작동하려면 **최소한의 RBAC 권한**이 필요합니다.

#### RMS 운영을 위한 최소 권한

```yaml
# ServiceAccount 생성
apiVersion: v1
kind: ServiceAccount
metadata:
  name: resource-manager-sa
  namespace: madp-system

---
# ClusterRole 정의 (전체 클러스터 권한)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: resource-manager-role
rules:
  # Namespace 관리
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["get", "list", "create", "update", "patch", "delete"]
  
  # ServiceAccount 관리 (모든 네임스페이스)
  - apiGroups: [""]
    resources: ["serviceaccounts"]
    verbs: ["get", "list", "create", "update", "patch", "delete"]
  
  # ConfigMap, Secret 관리
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "create", "update", "patch", "delete"]
  
  # Service 관리
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get", "list", "create", "update", "patch", "delete"]
  
  # Pod 조회 (관리 ❌, 조회만 ⭕)
  - apiGroups: [""]
    resources: ["pods", "pods/log", "pods/status"]
    verbs: ["get", "list", "watch"]
  
  # Deployment, StatefulSet 관리
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets"]
    verbs: ["get", "list", "create", "update", "patch", "delete"]
  
  # RBAC 관리
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources: ["roles", "rolebindings"]
    verbs: ["get", "list", "create", "update", "patch", "delete"]

---
# ClusterRoleBinding (ServiceAccount와 ClusterRole 연결)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: resource-manager-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: resource-manager-role
subjects:
  - kind: ServiceAccount
    name: resource-manager-sa
    namespace: madp-system
```

#### Deployment에 ServiceAccount 연결

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resource-manager
  namespace: madp-system
spec:
  template:
    spec:
      serviceAccountName: resource-manager-sa  # 👈 필수!
      containers:
        - name: resource-manager
          image: resource-manager:latest
          env:
            - name: K8S_USE_IN_CLUSTER_CONFIG
              value: "true"
```

### 3. 네트워크 및 연결 설정

#### 타임아웃 설정
```bash
# 기본값: 60초
export K8S_API_TIMEOUT=60

# 대규모 리소스 조회 시 타임아웃 증가
export K8S_API_TIMEOUT=120
```

**권장값**:
- **일반 조회**: 30-60초
- **대규모 목록 조회**: 90-120초
- **리소스 생성/삭제**: 60-90초

#### 재시도 설정
```bash
# 기본값: 3회
export K8S_MAX_RETRIES=3

# 불안정한 네트워크 환경에서는 증가
export K8S_MAX_RETRIES=5
```

**재시도 대상**:
- ✅ 네트워크 타임아웃
- ✅ 일시적인 API 서버 오류 (5xx)
- ❌ 권한 오류 (403) - 재시도 불필요
- ❌ 리소스 없음 (404) - 재시도 불필요

### 4. 보안 고려사항

#### 🔒 kubeconfig 파일 보호
```bash
# 파일 권한 제한
chmod 600 ~/.kube/config

# 소유권 확인
ls -la ~/.kube/config
# -rw------- 1 user group ... /home/user/.kube/config
```

#### 🔒 환경 변수 보호
```bash
# 민감한 정보는 Secret에서 로드
kubectl create secret generic k8s-config \
  --from-file=kubeconfig=/path/to/kubeconfig \
  --namespace=madp-system

# Deployment에서 Secret 마운트
volumeMounts:
  - name: kubeconfig
    mountPath: /var/secrets
    readOnly: true
volumes:
  - name: kubeconfig
    secret:
      secretName: k8s-config
```

#### 🔒 최소 권한 원칙
```yaml
# ❌ 나쁜 예: cluster-admin 권한 부여
subjects:
  - kind: ServiceAccount
    name: resource-manager-sa
roleRef:
  kind: ClusterRole
  name: cluster-admin  # 너무 강력한 권한!

# ✅ 좋은 예: 필요한 권한만 부여
roleRef:
  kind: ClusterRole
  name: resource-manager-role  # 커스텀 Role (최소 권한)
```

### 5. 로깅 및 모니터링

#### 로깅 설정

```python
# KubernetesClient는 자동으로 로그를 기록
# Logger 인스턴스를 주입하면 됨

from src.core import get_logger

logger = get_logger()
k8s_client = KubernetesClientImpl(k8s_config, logger)

# 로그 출력 예시:
# INFO: 클러스터 내부 Kubernetes 설정 로드 중
# INFO: Kubernetes 설정 로드 완료
# INFO: Kubernetes API 클라이언트 초기화 완료
```

#### 연결 상태 확인
```python
# 초기화 중 예외 발생 시 자동 로그 기록
try:
    await k8s_client.initialize()
except Exception as e:
    # 로그에 자동 기록됨:
    # ERROR: Kubernetes 설정 로드 실패: <상세 오류>
    raise
```

---

## 사용 패턴

### 1. 기본 사용 패턴 (의존성 주입)

```python
from fastapi import APIRouter, Depends
from src.infra.kubernetes.client import get_kubernetes_client, KubernetesClientImpl

router = APIRouter()


@router.get("/health/kubernetes")
async def check_kubernetes_health(
        k8s_client: KubernetesClientImpl = Depends(get_kubernetes_client)
):
    """Kubernetes 연결 상태 확인"""
    try:
        # Namespace 목록 조회로 연결 테스트
        await k8s_client.core_v1.list_namespace(limit=1)
        return {"status": "healthy", "message": "Kubernetes API 연결 정상"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}
```

### 2. 컨텍스트 매니저 패턴 (일회성 사용)

```python
from src.infra.kubernetes.client import KubernetesClientImpl
from src.common.config.kubernetes import KubernetesConfig
from src.core import get_logger


async def example_with_context_manager():
    """일회성 작업에 적합"""
    config = KubernetesConfig()
    logger = get_logger()

    # 자동으로 초기화 및 정리
    async with KubernetesClientImpl(config, logger) as k8s_client:
        namespaces = await k8s_client.core_v1.list_namespace()
        print(f"총 {len(namespaces.items)}개의 Namespace 존재")

    # 블록 종료 시 자동으로 close() 호출됨
```

### 3. 수동 생명주기 관리 (FastAPI 앱 이벤트)

```python
from fastapi import FastAPI
from src.infra.kubernetes.client import KubernetesClientImpl, get_kubernetes_client
from src.common.config.kubernetes import KubernetesConfig
from src.core import get_logger

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 Kubernetes 클라이언트 초기화"""
    config = KubernetesConfig()
    logger = get_logger()

    # 싱글톤 인스턴스 초기화
    k8s_client = await get_kubernetes_client(config, logger)
    logger.info("Kubernetes 클라이언트 초기화 완료")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 리소스 정리"""
    k8s_client = await get_kubernetes_client()
    await k8s_client.close()
    logger.info("Kubernetes 클라이언트 리소스 정리 완료")
```

### 4. Manager와 함께 사용

```python
from fastapi import APIRouter, Depends
from src.infra.kubernetes.client import get_kubernetes_client, KubernetesClientImpl
from src.infra.kubernetes.managers.namespace import NamespaceManager
from src.core import get_logger

router = APIRouter()


@router.post("/namespaces")
async def create_namespace(
        name: str,
        k8s_client: KubernetesClientImpl = Depends(get_kubernetes_client)
):
    """Namespace 생성 (Manager 활용)"""
    logger = get_logger()
    namespace_manager = NamespaceManager(k8s_client, logger)

    # Manager를 통한 멱등성 보장
    namespace = await namespace_manager.create_namespace(
        name=name,
        labels={"madp.io/managed-by": "resource-manager"}
    )

    return {
        "name": namespace.metadata.name,
        "uid": namespace.metadata.uid,
        "status": namespace.status.phase
    }
```

---

## 예외 처리

### 1. 초기화 실패 처리

```python
from src.infra.kubernetes.client import KubernetesClientImpl
from src.common.config.kubernetes import KubernetesConfig
from src.core import get_logger


async def initialize_with_error_handling():
    config = KubernetesConfig()
    logger = get_logger()
    k8s_client = KubernetesClientImpl(config, logger)

    try:
        await k8s_client.initialize()
    except FileNotFoundError as e:
        # kubeconfig 파일을 찾을 수 없음
        logger.error(f"kubeconfig 파일 없음: {e}")
        raise ValueError("Kubernetes 설정 파일이 없습니다. K8S_KUBECONFIG_PATH를 확인하세요.")
    except PermissionError as e:
        # kubeconfig 파일 권한 문제
        logger.error(f"kubeconfig 접근 권한 없음: {e}")
        raise ValueError("Kubernetes 설정 파일 접근 권한이 없습니다.")
    except Exception as e:
        # 기타 초기화 오류
        logger.error(f"Kubernetes 클라이언트 초기화 실패: {e}", exc_info=True)
        raise
```

### 2. API 호출 실패 처리

```python
from kubernetes_asyncio.client.exceptions import ApiException

async def handle_api_errors(k8s_client: KubernetesClientImpl):
    try:
        namespace = await k8s_client.core_v1.read_namespace(name="test-ns")
    except ApiException as e:
        if e.status == 404:
            # 리소스 없음
            print("Namespace가 존재하지 않습니다")
            return None
        elif e.status == 403:
            # 권한 없음
            print("Namespace 조회 권한이 없습니다")
            raise PermissionError(f"권한 부족: {e.reason}")
        elif e.status >= 500:
            # 서버 오류 (재시도 가능)
            print("Kubernetes API 서버 오류")
            raise
        else:
            # 기타 오류
            print(f"API 오류 ({e.status}): {e.reason}")
            raise
```

### 3. 연결 타임아웃 처리

```python
import asyncio

async def with_custom_timeout(k8s_client: KubernetesClientImpl):
    try:
        # 30초 타임아웃 설정
        namespaces = await asyncio.wait_for(
            k8s_client.core_v1.list_namespace(),
            timeout=30.0
        )
        return namespaces
    except asyncio.TimeoutError:
        logger.error("Kubernetes API 호출 타임아웃 (30초)")
        raise TimeoutError("Kubernetes API 응답 시간 초과")
```

---

## 모범 사례

### ✅ DO: 권장 사항

#### 1. 싱글톤 패턴 활용
```python
# ✅ 좋은 예: get_kubernetes_client() 사용
k8s_client = await get_kubernetes_client()

# ❌ 나쁜 예: 매번 새로운 인스턴스 생성
k8s_client = KubernetesClientImpl(config, logger)
await k8s_client.initialize()
```

#### 2. 의존성 주입 활용
```python
# ✅ 좋은 예: FastAPI 의존성 주입
@router.get("/namespaces")
async def list_namespaces(
    k8s_client: KubernetesClientImpl = Depends(get_kubernetes_client)
):
    pass

# ❌ 나쁜 예: 전역 변수 사용
global_k8s_client = None

@router.get("/namespaces")
async def list_namespaces():
    global global_k8s_client
    pass
```

#### 3. Manager 계층 활용
```python
# ✅ 좋은 예: Manager를 통한 추상화
namespace_manager = NamespaceManager(k8s_client, logger)
namespace = await namespace_manager.create_namespace(name="test-ns")

# ❌ 나쁜 예: 직접 API 호출 (예외 처리, 멱등성 보장 없음)
from kubernetes_asyncio.client import V1Namespace, V1ObjectMeta
ns = V1Namespace(metadata=V1ObjectMeta(name="test-ns"))
await k8s_client.core_v1.create_namespace(body=ns)
```

#### 4. 리소스 정리
```python
# ✅ 좋은 예: 컨텍스트 매니저 또는 명시적 close()
async with KubernetesClientImpl(config, logger) as k8s_client:
    # 작업 수행
    pass
# 자동으로 close() 호출됨

# 또는
k8s_client = KubernetesClientImpl(config, logger)
try:
    await k8s_client.initialize()
    # 작업 수행
finally:
    await k8s_client.close()

# ❌ 나쁜 예: 리소스 정리 없음
k8s_client = KubernetesClientImpl(config, logger)
await k8s_client.initialize()
# close() 호출 안 함 → 연결 누수!
```

#### 5. 환경별 설정 분리
```python
# ✅ 좋은 예: 환경 변수로 설정 관리
# .env.development
K8S_KUBECONFIG_PATH=/home/user/.kube/config
K8S_DEFAULT_NAMESPACE=default

# .env.production
K8S_USE_IN_CLUSTER_CONFIG=true
K8S_DEFAULT_NAMESPACE=madp-system

# ❌ 나쁜 예: 하드코딩
config = KubernetesConfig(
    kubeconfig_path="/home/user/.kube/config"  # 환경마다 변경 필요!
)
```

### ❌ DON'T: 피해야 할 사항

#### 1. 동기 블로킹 호출
```python
# ❌ 절대 금지: 동기 블로킹 호출
import time
time.sleep(10)  # FastAPI 이벤트 루프 블로킹!

# ✅ 올바른 방법: 비동기 대기
await asyncio.sleep(10)
```

#### 2. 과도한 API 호출
```python
# ❌ 나쁜 예: 반복문 내 개별 조회
for name in namespace_names:
    ns = await k8s_client.core_v1.read_namespace(name=name)

# ✅ 좋은 예: 한 번에 목록 조회 후 필터링
all_namespaces = await k8s_client.core_v1.list_namespace()
target_namespaces = [ns for ns in all_namespaces.items if ns.metadata.name in namespace_names]
```

#### 3. 권한 과다 부여
```yaml
# ❌ 나쁜 예: cluster-admin 권한 부여
roleRef:
  kind: ClusterRole
  name: cluster-admin

# ✅ 좋은 예: 필요한 권한만 부여
roleRef:
  kind: ClusterRole
  name: resource-manager-role  # 최소 권한
```

#### 4. 민감 정보 로깅
```python
# ❌ 나쁜 예: kubeconfig 내용 로깅
logger.info(f"kubeconfig: {open(kubeconfig_path).read()}")

# ✅ 좋은 예: 경로만 로깅
logger.info(f"kubeconfig 로드: {kubeconfig_path}")
```

---

## 트러블슈팅

### 문제 1: "Unable to load in-cluster configuration"
```
Error: Unable to load in-cluster configuration, KUBERNETES_SERVICE_HOST and KUBERNETES_SERVICE_PORT must be defined
```

**원인**: Pod 외부에서 in-cluster 설정을 사용하려고 시도

**해결책**:
```bash
# 로컬 개발 환경에서는 in-cluster 설정 비활성화
export K8S_USE_IN_CLUSTER_CONFIG=false
```

### 문제 2: "Forbidden: User cannot list resource"
```
ApiException: (403)
Reason: Forbidden
```

**원인**: ServiceAccount에 충분한 RBAC 권한이 없음

**해결책**:
```bash
# ServiceAccount 권한 확인
kubectl auth can-i list namespaces --as=system:serviceaccount:madp-system:resource-manager-sa

# ClusterRoleBinding 확인
kubectl get clusterrolebinding resource-manager-binding -o yaml
```

### 문제 3: "Connection timeout"
```
TimeoutError: Kubernetes API 응답 시간 초과
```

**원인**: 네트워크 지연 또는 API 서버 과부하

**해결책**:
```bash
# 타임아웃 증가
export K8S_API_TIMEOUT=120

# 재시도 횟수 증가
export K8S_MAX_RETRIES=5
```

---

## 참고 자료

- **kubernetes-asyncio 문서**: https://github.com/tomplus/kubernetes_asyncio
- **Kubernetes API 레퍼런스**: https://kubernetes.io/docs/reference/kubernetes-api/
- **RBAC 가이드**: https://kubernetes.io/docs/reference/access-authn-authz/rbac/
- **kubeconfig 설정**: https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/
- **Manager 가이드**: `/infra/kubernetes/managers/manager-guide.md`
- **M-ADP 프로젝트 설계**: `/CLAUDE.md`
