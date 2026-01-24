# ConfigMap Manager 가이드

## 개요

`ConfigMapManager`는 Kubernetes ConfigMap 리소스를 관리하는 클래스입니다. ConfigMap은 애플리케이션 설정 데이터를 키-값 쌍으로 저장하여 컨테이너 이미지와 설정을 분리합니다.

## 주요 기능

### 1. ConfigMap 생성
- **멱등성 보장**: 동일한 이름의 ConfigMap이 이미 존재하면 기존 리소스 반환
- **다양한 데이터 형식**: 문자열, 파일, 바이너리 데이터

```python
manager = ConfigMapManager(k8s_client)

# ConfigMap 생성
configmap = await manager.create_configmap(
    name="app-config",
    namespace="production",
    data={
        "database.url": "postgres://db.example.com:5432/mydb",
        "api.timeout": "30",
        "log.level": "info"
    }
)
```

### 2. 파일 기반 ConfigMap

```python
# 설정 파일 내용을 ConfigMap으로 저장
configmap = await manager.create_configmap(
    name="nginx-config",
    namespace="default",
    data={
        "nginx.conf": """
server {
    listen 80;
    server_name example.com;
    location / {
        proxy_pass http://backend:8080;
    }
}
"""
    }
)
```

### 3. ConfigMap 조회

```python
cm = await manager.get_configmap(
    name="app-config",
    namespace="production"
)

if cm:
    print(cm.data)
```

### 4. ConfigMap 업데이트

```python
configmap = await manager.update_configmap(
    name="app-config",
    namespace="production",
    data={
        "database.url": "postgres://new-db.example.com:5432/mydb",
        "api.timeout": "60"
    }
)
```

### 5. ConfigMap 삭제

```python
success = await manager.delete_configmap(
    name="app-config",
    namespace="production"
)
```

## Pod에서 ConfigMap 사용

### 1. 환경 변수로 사용

```python
from kubernetes_asyncio.client import V1EnvFromSource, V1ConfigMapEnvSource

container = V1Container(
    name="app",
    image="myapp:latest",
    env_from=[
        V1EnvFromSource(
            config_map_ref=V1ConfigMapEnvSource(
                name="app-config"
            )
        )
    ]
)
```

### 2. 특정 키만 환경 변수로

```python
from kubernetes_asyncio.client import V1EnvVar, V1EnvVarSource, V1ConfigMapKeySelector

container = V1Container(
    name="app",
    image="myapp:latest",
    env=[
        V1EnvVar(
            name="DB_URL",
            value_from=V1EnvVarSource(
                config_map_key_ref=V1ConfigMapKeySelector(
                    name="app-config",
                    key="database.url"
                )
            )
        )
    ]
)
```

### 3. 볼륨으로 마운트

```python
from kubernetes_asyncio.client import V1Volume, V1VolumeMount, V1ConfigMapVolumeSource

pod_spec = V1PodSpec(
    containers=[V1Container(
        name="app",
        image="nginx",
        volume_mounts=[
            V1VolumeMount(
                name="config-volume",
                mount_path="/etc/nginx"
            )
        ]
    )],
    volumes=[
        V1Volume(
            name="config-volume",
            config_map=V1ConfigMapVolumeSource(
                name="nginx-config"
            )
        )
    ]
)
```

## 사용 사례

### 1. 애플리케이션 설정
```python
await manager.create_configmap(
    name="app-settings",
    namespace="apps",
    data={
        "APP_ENV": "production",
        "CACHE_TTL": "3600",
        "MAX_CONNECTIONS": "100"
    }
)
```

### 2. 데이터베이스 연결 정보
```python
await manager.create_configmap(
    name="db-config",
    namespace="databases",
    data={
        "host": "postgres.databases.svc.cluster.local",
        "port": "5432",
        "database": "app_db"
    }
)
```

### 3. 애플리케이션 설정 파일
```python
await manager.create_configmap(
    name="app-properties",
    namespace="apps",
    data={
        "application.properties": """
spring.datasource.url=jdbc:postgresql://db:5432/app
spring.jpa.hibernate.ddl-auto=none
logging.level.root=INFO
"""
    }
)
```

## 멱등성 보장

- 동일한 이름의 ConfigMap 재생성 시 기존 리소스 반환

## 주의사항

1. **크기 제한**: ConfigMap은 최대 1MB
2. **민감 정보**: 비밀번호, API 키 등은 Secret 사용
3. **자동 업데이트**: Pod에 마운트된 ConfigMap 변경 시 자동 반영 (최대 수 분 소요)
4. **환경 변수**: 환경 변수로 사용 시 Pod 재시작 필요
5. **바이너리 데이터**: `binaryData` 필드 사용 (base64 인코딩)
6. **네임스페이스 스코프**: ConfigMap은 네임스페이스 리소스

## ConfigMap vs Secret

| 특징 | ConfigMap | Secret |
|------|-----------|--------|
| 용도 | 일반 설정 데이터 | 민감한 정보 |
| 인코딩 | 평문 | Base64 |
| 크기 제한 | 1MB | 1MB |
| 보안 | 일반 | 암호화 옵션 |

## 관련 리소스

- **Secret**: 민감한 설정 정보 저장
- **Pod/Deployment**: ConfigMap을 환경 변수 또는 볼륨으로 사용
- **Kustomize**: ConfigMap 생성 자동화
