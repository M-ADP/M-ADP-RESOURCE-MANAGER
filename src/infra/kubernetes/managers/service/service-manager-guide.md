# Service Manager 가이드

## 개요

`ServiceManager`는 Kubernetes Service 리소스를 관리하는 클래스입니다. Service는 Pod 집합에 대한 네트워크 접근을 제공하는 추상화 계층입니다.

## 주요 기능

### 1. Service 생성
- **멱등성 보장**: 동일한 이름의 Service가 이미 존재하면 기존 리소스 반환
- **다양한 타입 지원**: ClusterIP, NodePort, LoadBalancer, ExternalName

```python
from kubernetes_asyncio.client import V1ServicePort

manager = ServiceManager(k8s_client)

# ClusterIP Service (기본)
service = await manager.create_service(
    name="web-service",
    namespace="production",
    selector={"app_deployment": "web"},
    ports=[
        V1ServicePort(
            name="http",
            port=80,
            target_port=8080,
            protocol="TCP"
        )
    ],
    service_type="ClusterIP"
)
```

### 2. Service 타입

#### ClusterIP (기본)
- 클러스터 내부에서만 접근 가능
- 가장 일반적인 타입

```python
service = await manager.create_service(
    name="backend",
    namespace="default",
    selector={"app_deployment": "backend"},
    ports=[V1ServicePort(port=8080, target_port=8080)],
    service_type="ClusterIP"
)
```

#### NodePort
- 각 노드의 특정 포트로 외부 접근 가능
- 포트 범위: 30000-32767

```python
service = await manager.create_service(
    name="frontend",
    namespace="default",
    selector={"app_deployment": "frontend"},
    ports=[V1ServicePort(
        port=80,
        target_port=8080,
        node_port=30080
    )],
    service_type="NodePort"
)
```

#### LoadBalancer
- 클라우드 제공자의 로드 밸런서 생성
- 외부 IP 자동 할당

```python
service = await manager.create_service(
    name="public-api",
    namespace="default",
    selector={"app_deployment": "api"},
    ports=[V1ServicePort(port=443, target_port=8443)],
    service_type="LoadBalancer"
)
```

#### ExternalName
- 외부 DNS 이름으로 리다이렉트

```python
service = await manager.create_service(
    name="external-db",
    namespace="default",
    external_name="db.example.com",
    service_type="ExternalName"
)
```

### 3. Service 조회

```python
service = await manager.get_service(
    name="web-service",
    namespace="production"
)

if service:
    print(f"Cluster IP: {service.spec.cluster_ip}")
    print(f"Type: {service.spec.type}")
```

### 4. Service 삭제

```python
success = await manager.delete_service(
    name="web-service",
    namespace="production"
)
```

### 5. Service 목록 조회

```python
# 네임스페이스별 조회
services = await manager.list_services(namespace="production")

# 레이블 셀렉터로 필터링
services = await manager.list_services(
    namespace="production",
    label_selector="app_deployment=web"
)
```

## 세션 어피니티 (Session Affinity)

동일한 클라이언트 요청을 같은 Pod로 라우팅:

```python
service = await manager.create_service(
    name="stateful-app_deployment",
    namespace="default",
    selector={"app_deployment": "stateful"},
    ports=[V1ServicePort(port=80, target_port=8080)],
    session_affinity="ClientIP"  # None (기본) 또는 ClientIP
)
```

## Headless Service

Pod IP를 직접 반환 (로드 밸런싱 없음):

```python
service = await manager.create_service(
    name="database",
    namespace="default",
    selector={"app_deployment": "database"},
    ports=[V1ServicePort(port=5432, target_port=5432)],
    cluster_ip="None"  # Headless
)
```

## 사용 사례

### 1. 마이크로서비스 통신
```python
# 서비스 간 통신
await manager.create_service(
    name="user-service",
    namespace="services",
    selector={"app_deployment": "user"},
    ports=[V1ServicePort(port=80, target_port=8080)]
)
# 다른 서비스에서 user-service.services.svc.cluster.local로 접근
```

### 2. 데이터베이스 접근
```python
# StatefulSet의 Headless Service
await manager.create_service(
    name="postgres",
    namespace="databases",
    selector={"app_deployment": "postgres"},
    ports=[V1ServicePort(port=5432, target_port=5432)],
    cluster_ip="None"
)
```

### 3. 외부 노출
```python
# LoadBalancer로 외부 노출
await manager.create_service(
    name="public-web",
    namespace="frontend",
    selector={"app_deployment": "web"},
    ports=[V1ServicePort(port=80, target_port=8080)],
    service_type="LoadBalancer"
)
```

## 멱등성 보장

- 동일한 이름의 Service 재생성 시 기존 리소스 반환

## 주의사항

1. **셀렉터 필수**: ExternalName을 제외한 모든 타입에서 필수
2. **포트 충돌**: NodePort 사용 시 포트 충돌 주의
3. **LoadBalancer 비용**: 클라우드 제공자의 로드 밸런서 비용 발생
4. **ClusterIP 변경 불가**: 생성 후 ClusterIP 변경 불가
5. **Headless Service**: `cluster_ip="None"` 설정 시 ClusterIP 할당 안 됨

## 관련 리소스

- **Pod/Deployment**: Service가 트래픽을 라우팅할 대상
- **Endpoints**: Service가 자동으로 생성/관리
- **Ingress**: HTTP/HTTPS 라우팅 (Layer 7)
- **NetworkPolicy**: Service 간 네트워크 격리
