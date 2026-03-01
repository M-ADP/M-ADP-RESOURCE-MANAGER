# Secret Manager 가이드

## 개요

`SecretManager`는 Kubernetes Secret 리소스를 관리하는 클래스입니다. Secret은 비밀번호, OAuth 토큰, SSH 키와 같은 민감한 정보를 저장합니다.

**중요**: RMS는 Vault 통합을 전제로 하며, Secret 값을 직접 관리하지 않고 Secret 접근 구조만 관리합니다.

## 주요 기능

### 1. Secret 생성
- **멱등성 보장**: 동일한 이름의 Secret이 이미 존재하면 기존 리소스 반환
- **Base64 자동 인코딩**: 데이터는 자동으로 인코딩됨

```python
manager = SecretManager(k8s_client)

# Opaque Secret (기본 타입)
secret = await manager.create_secret(
    name="db-credentials",
    namespace="production",
    data={
        "username": "admin",       # 자동 base64 인코딩
        "password": "secret123"
    },
    secret_type="Opaque"
)
```

### 2. Secret 타입

#### Opaque (기본)
- 일반적인 키-값 데이터

```python
secret = await manager.create_secret(
    name="api-keys",
    namespace="default",
    data={
        "api-key": "abc123xyz",
        "api-secret": "xyz789abc"
    }
)
```

#### kubernetes.io/dockerconfigjson
- Docker 레지스트리 인증

```python
import json
import base64

docker_config = {
    "auths": {
        "https://index.docker.io/v1/": {
            "username": "user",
            "password": "pass",
            "email": "user@example.com",
            "auth": base64.b64encode(b"user:pass").decode()
        }
    }
}

secret = await manager.create_secret(
    name="docker-registry",
    namespace="default",
    data={
        ".dockerconfigjson": json.dumps(docker_config)
    },
    secret_type="kubernetes.io/dockerconfigjson"
)
```

#### kubernetes.io/tls
- TLS 인증서

```python
secret = await manager.create_secret(
    name="tls-cert",
    namespace="default",
    data={
        "tls.crt": cert_content,  # 인증서
        "tls.key": key_content    # 개인 키
    },
    secret_type="kubernetes.io/tls"
)
```

#### kubernetes.io/basic-auth
- 기본 인증

```python
secret = await manager.create_secret(
    name="basic-auth",
    namespace="default",
    data={
        "username": "admin",
        "password": "password123"
    },
    secret_type="kubernetes.io/basic-auth"
)
```

### 3. Secret 조회

```python
secret = await manager.get_secret(
    name="db-credentials",
    namespace="production"
)

if secret:
    # 데이터는 base64로 인코딩되어 있음
    import base64
    username = base64.b64decode(secret.data["username"]).decode()
```

### 4. Secret 삭제

```python
success = await manager.delete_secret(
    name="db-credentials",
    namespace="production"
)
```

## Pod에서 Secret 사용

### 1. 환경 변수로 사용

```python
from kubernetes_asyncio.client import V1EnvVar, V1EnvVarSource, V1SecretKeySelector

container = V1Container(
    name="app_deployment",
    image="myapp:latest",
    env=[
        V1EnvVar(
            name="DB_PASSWORD",
            value_from=V1EnvVarSource(
                secret_key_ref=V1SecretKeySelector(
                    name="db-credentials",
                    key="password"
                )
            )
        )
    ]
)
```

### 2. 볼륨으로 마운트

```python
from kubernetes_asyncio.client import V1Volume, V1VolumeMount, V1SecretVolumeSource

pod_spec = V1PodSpec(
    containers=[V1Container(
        name="app_deployment",
        image="myapp",
        volume_mounts=[
            V1VolumeMount(
                name="secret-volume",
                mount_path="/etc/secrets",
                read_only=True
            )
        ]
    )],
    volumes=[
        V1Volume(
            name="secret-volume",
            secret=V1SecretVolumeSource(
                secret_name="db-credentials"
            )
        )
    ]
)
```

## RMS에서의 Secret 관리

RMS는 Vault 통합을 통해 Secret을 관리합니다:

1. **Secret 값 미저장**: Secret의 실제 값은 Vault에 저장
2. **접근 구조 관리**: ServiceAccount ↔ Vault Role 연결
3. **주입 방식**: Workload에 Vault Agent 주입

## 사용 사례

### 1. 데이터베이스 인증
```python
await manager.create_secret(
    name="postgres-creds",
    namespace="databases",
    data={
        "username": "dbuser",
        "password": "dbpass123"
    }
)
```

### 2. API 키
```python
await manager.create_secret(
    name="external-api",
    namespace="services",
    data={
        "api-key": "sk_live_abc123xyz",
        "api-secret": "secret_xyz789"
    }
)
```

### 3. TLS 인증서
```python
await manager.create_secret(
    name="web-tls",
    namespace="frontend",
    data={
        "tls.crt": cert_pem,
        "tls.key": key_pem
    },
    secret_type="kubernetes.io/tls"
)
```

## 보안 권장사항

1. **RBAC 제한**: Secret 접근을 최소 권한으로 제한
2. **암호화**: etcd 암호화 활성화 권장
3. **Vault 사용**: 가능한 Vault와 같은 외부 Secret 관리 도구 사용
4. **환경 변수 주의**: 환경 변수는 로그에 노출될 수 있음
5. **버전 관리 금지**: Secret을 Git에 커밋하지 말 것
6. **정기 교체**: Secret을 정기적으로 교체

## 멱등성 보장

- 동일한 이름의 Secret 재생성 시 기존 리소스 반환

## 주의사항

1. **크기 제한**: Secret은 최대 1MB
2. **Base64 인코딩**: 암호화가 아닌 인코딩 (보안 X)
3. **자동 업데이트**: 볼륨 마운트 시 자동 업데이트 (환경 변수는 재시작 필요)
4. **네임스페이스 스코프**: Secret은 네임스페이스 리소스
5. **immutable**: `immutable: true` 설정 시 변경 불가 (성능 향상)

## 관련 리소스

- **ConfigMap**: 일반 설정 데이터 (민감하지 않은 정보)
- **ServiceAccount**: Secret을 자동으로 마운트
- **Vault**: 외부 Secret 관리 시스템 (RMS 권장)
- **Pod/Deployment**: Secret을 환경 변수 또는 볼륨으로 사용
