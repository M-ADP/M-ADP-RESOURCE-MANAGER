# Vault 클라이언트 가이드

## 목차
1. [개요](#개요)
2. [역할 및 책임](#역할-및-책임)
3. [아키텍처](#아키텍처)
4. [주요 기능](#주요-기능)
5. [사용 방법](#사용-방법)
6. [유의사항](#유의사항)
7. [FAQ](#faq)

---

## 개요

### Vault란?

HashiCorp Vault는 민감한 데이터(Secret)를 안전하게 저장하고 접근을 제어하는 도구입니다.

### RMS에서의 Vault 역할

```
┌─────────────────────────────────────────────────┐
│  RMS (Resource Manager Server)                  │
│                                                  │
│  ┌──────────────┐         ┌──────────────┐     │
│  │ Secret       │  사용   │ Vault        │     │
│  │ Manager      │ ──────> │ Client       │     │
│  └──────────────┘         └──────────────┘     │
│                                    │            │
└────────────────────────────────────┼────────────┘
                                     │
                                     │ hvac SDK
                                     ▼
                            ┌─────────────────┐
                            │  Vault Server   │
                            │                 │
                            │  - Policies     │
                            │  - Roles        │
                            │  - Secrets      │
                            └─────────────────┘
```

**핵심 원칙:**
- ✅ RMS는 Vault를 통해 Secret **값**을 저장하고 관리한다
- ✅ RMS는 Secret **접근 구조**(Policy, Role)도 관리한다
- ✅ Secret 값은 오직 Vault에만 존재한다 (Kubernetes Secret 리소스는 사용하지 않음)

---

## 역할 및 책임

### VaultClient의 역할

| 역할 | 설명 |
|------|------|
| **Vault API 추상화** | hvac SDK를 사용하여 Vault API를 간단하게 호출 |
| **비동기 인터페이스 제공** | run_in_executor로 동기 hvac를 비동기로 래핑 |
| **에러 처리** | Vault 에러를 RMS 커스텀 예외로 변환 |
| **로깅** | 모든 Vault 작업을 로깅하여 추적 가능 |

### VaultClient가 하는 것 ✅

1. **Kubernetes Auth Role 관리**
   - ServiceAccount가 Vault에 인증할 수 있도록 Role 생성
   - Role 조회, 삭제, 목록 조회

2. **Policy 관리**
   - Secret 경로별 접근 권한 정의
   - Policy 생성, 조회, 삭제, 목록 조회

3. **Secret 값 관리 (KV v2)**
   - Vault에 Secret 생성/저장
   - Secret 조회 및 버전 관리
   - Secret 삭제 (모든 버전)
   - Secret 목록 조회

4. **Health Check**
   - Vault 서버 상태 확인

### VaultClient가 하지 않는 것 ❌

1. **Kubernetes Secret 리소스 생성**
   - Kubernetes의 Secret 리소스는 사용하지 않음
   - 모든 Secret은 Vault에만 저장

2. **인증 토큰 발급**
   - Pod가 직접 Vault에 인증하여 토큰 획득
   - RMS는 인증 구조만 설정

3. **Secret 암호화**
   - Vault가 자동으로 암호화 처리
   - RMS는 평문을 Vault에 전달

---

## 아키텍처

### 계층 구조

```
┌─────────────────────────────────────────────────────┐
│  Application Layer                                   │
│  ┌──────────────────────────────────────────────┐   │
│  │  Secret Manager                              │   │
│  │  - bind_serviceaccount_to_vault()           │   │
│  │  - inject_vault_agent_to_deployment()       │   │
│  │  - setup_secret_access()                    │   │
│  └──────────────────────────────────────────────┘   │
│                      │                               │
│                      ▼                               │
│  ┌──────────────────────────────────────────────┐   │
│  │  Vault Client                                │   │
│  │  - create_secret()                           │   │
│  │  - create_kubernetes_role()                  │   │
│  │  - create_policy()                           │   │
│  │  - _run_in_executor()                        │   │
│  └──────────────────────────────────────────────┘   │
│                      │                               │
└──────────────────────┼───────────────────────────────┘
                       │
                       ▼
           ┌────────────────────────┐
           │  hvac SDK              │
           │  - client.auth.k8s     │
           │  - client.sys          │
           └────────────────────────┘
                       │
                       ▼
           ┌────────────────────────┐
           │  Vault HTTP API        │
           └────────────────────────┘
```

### Secret 접근 흐름

```
1. RMS가 Vault에 정책 설정
   RMS → VaultClient.create_policy()
   → Vault Policy 생성: "secret/data/app/* 읽기 허용"

2. RMS가 ServiceAccount와 Policy 연결
   RMS → VaultClient.create_kubernetes_role()
   → Vault Role 생성: "SA test-sa가 Policy test-policy 사용 가능"

3. Pod가 Vault에 인증하여 Secret 획득
   Pod → Vault: "나는 SA test-sa입니다"
   Vault → Pod: "토큰 발급"
   Pod → Vault: "secret/data/app/db 읽기"
   Vault → Pod: {"username": "admin", "password": "..."}
```

---

## 주요 기능

### 1. Kubernetes Auth Role 관리

#### Role 생성

```python
from src.infra import VaultClient

vault_client = VaultClient(
    vault_addr="http://vault.default.svc.cluster.local:8200",
    vault_token="root-token",
)

# Kubernetes Auth Role 생성
await vault_client.create_kubernetes_role(
    role_name="my-app_deployment-role",
    bound_service_account_names=["my-app_deployment-sa"],
    bound_service_account_namespaces=["default"],
    policies=["my-app_deployment-policy"],
    ttl="1h",
    max_ttl="24h",
)
```

#### Role 조회
```python
role = await vault_client.get_kubernetes_role("my-app_deployment-role")
print(role)
# {
#   "bound_service_account_names": ["my-app_deployment-sa"],
#   "bound_service_account_namespaces": ["default"],
#   "policies": ["my-app_deployment-policy"],
#   ...
# }
```

#### Role 삭제
```python
await vault_client.delete_kubernetes_role("my-app_deployment-role")
```

#### Role 목록 조회
```python
roles = await vault_client.list_kubernetes_roles()
print(roles)  # ["my-app_deployment-role", "another-role", ...]
```

### 2. Policy 관리

#### Policy 생성
```python
# Policy HCL 생성
policy_hcl = VaultClient.generate_policy_hcl(
    secret_paths=[
        "secret/data/myapp/db",
        "secret/data/myapp/api-key",
    ],
    capabilities=["read"],
)

# Policy 생성
await vault_client.create_policy(
    policy_name="my-app_deployment-policy",
    policy_hcl=policy_hcl,
)
```

생성되는 Policy HCL:
```hcl
path "secret/data/myapp/db" {
  capabilities = ["read"]
}

path "secret/data/myapp/api-key" {
  capabilities = ["read"]
}
```

#### Policy 조회
```python
policy = await vault_client.get_policy("my-app_deployment-policy")
print(policy)  # HCL 문자열
```

#### Policy 삭제
```python
await vault_client.delete_policy("my-app_deployment-policy")
```

### 3. Secret 값 관리 (KV v2)

#### Secret 생성/저장
```python
# Secret 데이터를 Vault에 저장
await vault_client.create_secret(
    path="myapp/db",
    secret={
        "username": "admin",
        "password": "Hashi123",
        "host": "postgres.default.svc.cluster.local",
        "port": "5432",
    },
    mount_point="secret",  # 기본값: "secret"
)
```

**주의사항:**
- `path`는 "myapp/db" 형식 (자동으로 "secret/data/myapp/db"로 변환)
- KV v2 엔진 사용 (버전 관리 지원)
- 동일 경로에 재저장 시 새 버전 생성

#### Secret 조회
```python
# 최신 버전 조회
secret = await vault_client.get_secret("myapp/db")
print(secret)
# {
#   "username": "admin",
#   "password": "Hashi123",
#   "host": "postgres.default.svc.cluster.local",
#   "port": "5432"
# }

# 특정 버전 조회
secret_v1 = await vault_client.get_secret("myapp/db", version=1)
```

#### Secret 삭제
```python
# 모든 버전 삭제 (메타데이터 포함)
await vault_client.delete_secret("myapp/db")
```

**주의:** 이 작업은 되돌릴 수 없습니다!

#### Secret 목록 조회
```python
# 루트 경로의 Secret 목록
secrets = await vault_client.list_secrets("")
print(secrets)  # ["myapp/", "shared/"]

# 특정 디렉토리의 Secret 목록
app_secrets = await vault_client.list_secrets("myapp/")
print(app_secrets)  # ["db", "api-key", "jwt-secret"]
```

### 4. Health Check

```python
is_healthy = await vault_client.health_check()
if is_healthy:
    print("Vault 서버 정상")
else:
    print("Vault 서버 이상")
```

---

## 사용 방법

### 기본 사용 (Secret Manager를 통한 사용 권장)

```python
from src.infra.kubernetes.client import KubernetesClientImpl
from src.infra import VaultClient
from src.infra.kubernetes.managers.secret import SecretManager

# 클라이언트 초기화
k8s_client = KubernetesClientImpl(...)
vault_client = VaultClient(
    vault_addr="http://vault.default.svc.cluster.local:8200",
    vault_token="root-token",
)

# Secret Manager 사용 (권장)
secret_manager = SecretManager(k8s_client, vault_client)

# 1. Secret 값을 Vault에 저장
await vault_client.create_secret(
    path="myapp/db",
    secret={
        "username": "admin",
        "password": "Hashi123",
        "host": "postgres.default.svc.cluster.local",
    },
)

await vault_client.create_secret(
    path="myapp/api-key",
    secret={"key": "sk-1234567890abcdef"},
)

# 2. 접근 권한 설정
await secret_manager.setup_secret_access(
    service_account_name="my-app_deployment-sa",
    namespace="default",
    secret_paths=[
        "secret/data/myapp/db",
        "secret/data/myapp/api-key",
    ],
)
```

### 직접 VaultClient 사용 (고급)

```python
# 1. Secret 값 저장
await vault_client.create_secret(
    path="myapp/db",
    secret={"username": "admin", "password": "secret123"},
)

# 2. Policy 생성
policy_hcl = VaultClient.generate_policy_hcl(
    secret_paths=["secret/data/myapp/*"],
    capabilities=["read"],
)
await vault_client.create_policy("my-policy", policy_hcl)

# 3. Role 생성
await vault_client.create_kubernetes_role(
    role_name="my-role",
    bound_service_account_names=["my-sa"],
    bound_service_account_namespaces=["default"],
    policies=["my-policy"],
)

# 4. 확인
secret = await vault_client.get_secret("myapp/db")
role = await vault_client.get_kubernetes_role("my-role")
policy = await vault_client.get_policy("my-policy")
```

---

## 유의사항

### ⚠️ 중요한 제약사항

#### 1. Secret 저장 시 경로 주의

```python
# ❌ 잘못된 경로 (data 포함하지 않음)
await vault_client.create_secret(
    path="secret/data/myapp/db",  # ❌ data는 자동 추가됨!
    secret={"password": "secret123"}
)

# ✅ 올바른 경로
await vault_client.create_secret(
    path="myapp/db",  # ✅ 올바른 형식
    secret={"password": "secret123"}
)
# 실제 저장 경로: secret/data/myapp/db (KV v2 자동 변환)
```

**중요:**
- VaultClient는 KV v2 엔진 사용
- `path` 파라미터는 "myapp/db" 형식으로 전달
- hvac가 자동으로 "secret/data/myapp/db"로 변환
- Policy 설정 시에는 "secret/data/myapp/db" 전체 경로 사용

#### 2. 비동기 처리 필수

```python
# ❌ 동기 호출 불가
role = vault_client.create_kubernetes_role(...)  # 에러!

# ✅ 비동기 호출
role = await vault_client.create_kubernetes_role(...)  # 정상
```

#### 3. run_in_executor 제한

hvac는 동기 라이브러리이므로 run_in_executor를 사용합니다.
대량의 요청 시 ThreadPoolExecutor의 기본 스레드 수 제한에 주의하세요.

```python
# 대량 작업 시 주의
tasks = []
for i in range(1000):  # 너무 많은 동시 작업
    tasks.append(vault_client.create_kubernetes_role(...))
await asyncio.gather(*tasks)  # ThreadPool 고갈 가능
```

#### 4. Vault 토큰 관리

```python
# ❌ 토큰을 코드에 하드코딩
vault_client = VaultClient(
    vault_addr="...",
    vault_token="s.abc123xyz",  # 위험!
)

# ✅ 환경변수 또는 Secret에서 로드
import os
vault_client = VaultClient(
    vault_addr=os.getenv("VAULT_ADDR"),
    vault_token=os.getenv("VAULT_TOKEN"),
)
```

#### 5. Policy 경로 패턴 주의

```python
# ❌ 너무 광범위한 권한
policy_hcl = VaultClient.generate_policy_hcl(
    secret_paths=["secret/data/*"],  # 모든 Secret 접근 가능!
    capabilities=["read", "create", "update", "delete"],  # 모든 권한!
)

# ✅ 최소 권한 원칙
policy_hcl = VaultClient.generate_policy_hcl(
    secret_paths=["secret/data/myapp/db"],  # 특정 경로만
    capabilities=["read"],  # 읽기만
)
```

### 🔒 보안 모범 사례

1. **최소 권한 원칙**
   - 필요한 Secret 경로만 허용
   - 필요한 capabilities만 부여 (대부분 read만으로 충분)

2. **TTL 설정**
   - 토큰 유효 시간을 적절히 제한 (기본: 1시간)
   - max_ttl로 최대 시간 제한

3. **Namespace 격리**
   - ServiceAccount는 해당 Namespace에만 바인딩
   - 크로스 네임스페이스 접근 금지

4. **감사 로그**
   - Vault의 audit log 활성화
   - RMS 로그와 함께 모니터링

---

## FAQ

### Q1. Secret 값은 어디에 저장하나요?

**A:** Secret 값은 Vault에만 저장됩니다. RMS는 VaultClient를 통해 Vault에 저장합니다.

```python
# RMS를 통한 Secret 저장 (권장)
await vault_client.create_secret(
    path="myapp/db",
    secret={"username": "admin", "password": "secret123"}
)

# 또는 Vault CLI 직접 사용도 가능 (운영자)
# vault kv put secret/myapp/db username=admin password=secret123

# 이후 접근 권한 설정 (자동화)
await secret_manager.setup_secret_access(
    service_account_name="myapp-sa",
    namespace="default",
    secret_paths=["secret/data/myapp/db"],  # 위에서 저장한 Secret
)
```

**중요:**
- Kubernetes Secret 리소스는 사용하지 않음
- 모든 Secret은 Vault에 저장되어 자동 암호화됨
- RMS는 Vault API를 통해 안전하게 관리

### Q2. Pod는 어떻게 Secret을 가져오나요?

**A:** Vault Agent Injector 또는 Secrets Store CSI Driver를 사용합니다.

```yaml
# Vault Agent Injector (RMS가 자동 주입)
apiVersion: v1
kind: Pod
metadata:
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/role: "myapp-role"
    vault.hashicorp.com/agent-inject-secret-db: "secret/data/myapp/db"
spec:
  serviceAccountName: myapp-sa
```

Pod 시작 시:
1. Vault Agent가 사이드카로 주입됨
2. Agent가 ServiceAccount 토큰으로 Vault 인증
3. Secret을 파일로 마운트: `/vault/secrets/db`

### Q3. hvac와 aiohttp 중 왜 hvac를 선택했나요?

**A:** 공식 SDK의 안정성과 유지보수성이 더 중요하기 때문입니다.

| hvac | aiohttp (직접 구현) |
|------|---------------------|
| ✅ 공식 지원 | ❌ 직접 유지보수 |
| ✅ 자동 업데이트 | ❌ 수동 업데이트 |
| ✅ 검증된 안정성 | ❌ 직접 테스트 |
| ❌ 동기 방식 | ✅ 네이티브 비동기 |

run_in_executor로 비동기 래핑하여 단점을 보완했습니다.

### Q4. Vault가 다운되면 어떻게 되나요?

**A:** 새로운 Pod는 시작할 수 없지만, 기존 Pod는 영향 없습니다.

- **신규 Pod:** Secret 획득 실패 → 시작 실패
- **기존 Pod:** 이미 메모리/파일에 Secret 보유 → 정상 동작
- **RMS:** Vault 작업 실패 → 에러 로그 및 예외 발생

**복구:**
1. Vault 서버 재시작
2. RMS는 자동으로 재연결 (다음 요청부터 정상)

### Q5. 여러 Namespace에서 같은 Secret을 사용할 수 있나요?

**A:** 각 Namespace마다 별도의 Role과 Policy가 필요합니다.

```python
# Namespace A
await secret_manager.setup_secret_access(
    service_account_name="app_deployment-sa",
    namespace="namespace-a",
    secret_paths=["secret/data/shared/db"],
)

# Namespace B (별도 설정 필요)
await secret_manager.setup_secret_access(
    service_account_name="app_deployment-sa",
    namespace="namespace-b",
    secret_paths=["secret/data/shared/db"],  # 같은 Secret
)
```

두 Namespace는 다른 Role을 사용하지만 같은 Secret에 접근할 수 있습니다.

### Q6. RMS가 Secret을 관리한다는 것은 무엇을 의미하나요?

**A:** RMS는 두 가지를 모두 관리합니다:

1. **Secret 값 관리 (Vault 사용)**
   ```python
   # Secret 저장
   await vault_client.create_secret(path="myapp/db", secret={...})
   
   # Secret 조회
   secret = await vault_client.get_secret("myapp/db")
   
   # Secret 삭제
   await vault_client.delete_secret("myapp/db")
   ```

2. **Secret 접근 구조 관리 (Policy + Role)**
   ```python
   # 누가(ServiceAccount) 어떤 Secret에 접근할 수 있는지 설정
   await secret_manager.setup_secret_access(
       service_account_name="myapp-sa",
       namespace="default",
       secret_paths=["secret/data/myapp/db"],
   )
   ```

**하지만 RMS가 하지 않는 것:**
- ❌ Kubernetes Secret 리소스 생성 (사용하지 않음)
- ❌ Secret 암호화 (Vault가 자동 처리)
- ❌ 애플리케이션에 직접 Secret 전달 (Vault Agent가 처리)

### Q7. Secret을 업데이트하려면 어떻게 하나요?

**A:** `create_secret()`을 동일 경로에 다시 호출하면 새 버전이 생성됩니다.

```python
# 초기 버전 생성 (version 1)
await vault_client.create_secret(
    path="myapp/db",
    secret={"password": "old-password"}
)

# 업데이트 (version 2 자동 생성)
await vault_client.create_secret(
    path="myapp/db",
    secret={"password": "new-password"}  # 같은 경로에 재저장
)

# 이전 버전 조회도 가능
old_secret = await vault_client.get_secret("myapp/db", version=1)
new_secret = await vault_client.get_secret("myapp/db")  # 최신 버전
```

**버전 관리:**
- KV v2 엔진은 자동으로 버전 관리
- 기본적으로 10개 버전까지 보관 (Vault 설정)
- 이전 버전으로 롤백 가능

---

## 참고 자료

- [HashiCorp Vault 공식 문서](https://www.vaultproject.io/docs)
- [hvac SDK 문서](https://hvac.readthedocs.io/)
- [Vault Kubernetes Auth](https://www.vaultproject.io/docs/auth/kubernetes)
- [Vault Agent Injector](https://www.vaultproject.io/docs/platform/k8s/injector)
- [Secrets Store CSI Driver](https://secrets-store-csi-driver.sigs.k8s.io/)

---

## 버전 정보

- **Vault Client Version:** 1.0.0
- **hvac Version:** ^2.0.0
- **Vault Server:** ^1.12.0 이상 권장
- **Python:** 3.12+
