# StatefulSet Manager 가이드

## 개요

StatefulSet Manager는 **상태를 유지하는 애플리케이션(Stateful Application)**을 위한 Kubernetes StatefulSet 리소스를 관리합니다.

StatefulSet은 다음과 같은 특징을 가진 워크로드에 사용됩니다:
- **안정적인 네트워크 식별자**: 각 Pod가 고유하고 예측 가능한 이름을 가짐 (예: `myapp-0`, `myapp-1`)
- **안정적인 영구 스토리지**: 각 Pod가 자신만의 PersistentVolume을 가짐
- **순서 보장**: Pod 생성/삭제/업데이트가 순서대로 진행됨
- **고유한 신원 유지**: Pod가 재시작되어도 동일한 이름과 스토리지를 유지

대표적인 사용 사례:
- 데이터베이스 (MySQL, PostgreSQL, MongoDB 클러스터)
- 분산 시스템 (Kafka, ZooKeeper, Cassandra)
- 영구 데이터를 가진 애플리케이션

---

## 주요 기능

### 1. StatefulSet 생성 (멱등성 보장)

```python
from kubernetes_asyncio.client import V1Container, V1PersistentVolumeClaim, V1ResourceRequirements

# StatefulSet 생성
statefulset = await manager.create_statefulset(
    name="mysql-cluster",
    namespace="production",
    service_name="mysql-headless",  # Headless Service 이름 (필수)
    replicas=3,
    selector={"app": "mysql", "role": "db"},
    containers=[
        V1Container(
            name="mysql",
            image="mysql:8.0",
            ports=[{"containerPort": 3306}],
            env=[
                {"name": "MYSQL_ROOT_PASSWORD", "value": "changeme"}
            ]
        )
    ],
    labels={"app": "mysql", "tier": "database"},
    volume_claim_templates=[
        V1PersistentVolumeClaim(
            metadata={"name": "data"},
            spec={
                "accessModes": ["ReadWriteOnce"],
                "resources": V1ResourceRequirements(
                    requests={"storage": "10Gi"}
                )
            }
        )
    ],
    update_strategy="RollingUpdate",  # 또는 "OnDelete"
    pod_management_policy="OrderedReady"  # 또는 "Parallel"
)

print(f"StatefulSet 생성됨: {statefulset.metadata.name}")
print(f"Service: {statefulset.spec.service_name}")
print(f"Replicas: {statefulset.spec.replicas}")
```

**Update Strategy:**
- `RollingUpdate`: Pod를 하나씩 순서대로 업데이트 (기본값)
- `OnDelete`: 수동으로 Pod를 삭제해야 업데이트됨

**Pod Management Policy:**
- `OrderedReady`: Pod를 순서대로 생성/삭제 (myapp-0 → myapp-1 → myapp-2)
- `Parallel`: 모든 Pod를 동시에 생성/삭제

### 2. StatefulSet 조회

```python
# 단일 StatefulSet 조회
sts = await manager.get_statefulset("mysql-cluster", "production")
if sts:
    print(f"StatefulSet 발견: {sts.metadata.name}")
    print(f"현재 Replicas: {sts.status.ready_replicas}/{sts.spec.replicas}")
else:
    print("StatefulSet이 존재하지 않음")

# 존재 여부 확인
exists = await manager.exists("mysql-cluster", "production")
```

### 3. StatefulSet 목록 조회

```python
# 특정 네임스페이스의 모든 StatefulSet
statefulsets = await manager.list_statefulsets(namespace="production")

# 레이블 셀렉터로 필터링
db_statefulsets = await manager.list_statefulsets(
    namespace="production",
    label_selector="tier=database"
)

# 전체 클러스터의 StatefulSet
all_statefulsets = await manager.list_statefulsets()
```

### 4. StatefulSet 스케일 조정

```python
# Replica 개수 변경
updated = await manager.scale_statefulset(
    name="mysql-cluster",
    namespace="production",
    replicas=5  # 3 → 5로 확장
)

print(f"Replicas: {updated.spec.replicas}")
```

**주의:**
- **스케일 업**: 새로운 Pod가 순서대로 생성됨 (myapp-3, myapp-4)
- **스케일 다운**: 역순으로 Pod가 삭제됨 (myapp-4, myapp-3)
- **PVC는 자동 삭제되지 않음**: 스케일 다운 시 PVC는 남아있음 (데이터 보존)

### 5. StatefulSet 상태 조회

```python
status = await manager.get_statefulset_status("mysql-cluster", "production")
if status:
    print(f"Total Replicas: {status['replicas']}")
    print(f"Ready Replicas: {status['ready_replicas']}")
    print(f"Current Replicas: {status['current_replicas']}")
    print(f"Updated Replicas: {status['updated_replicas']}")
    print(f"Current Revision: {status['current_revision']}")
    print(f"Update Revision: {status['update_revision']}")

# 준비 상태 확인
is_ready = await manager.is_ready("mysql-cluster", "production")
if is_ready:
    print("모든 Pod가 준비되었습니다")
```

### 6. 레이블 및 어노테이션 업데이트

```python
# 레이블 추가/병합
updated = await manager.update_labels(
    name="mysql-cluster",
    namespace="production",
    labels={"environment": "prod", "version": "v2"},
    merge=True  # 기존 레이블과 병합
)

# 어노테이션 추가
updated = await manager.update_annotations(
    name="mysql-cluster",
    namespace="production",
    annotations={"monitoring": "enabled"},
    merge=True
)
```

### 7. StatefulSet 삭제

```python
# StatefulSet 삭제 (Pod와 Service도 함께 삭제됨)
success = await manager.delete_statefulset(
    name="mysql-cluster",
    namespace="production",
    grace_period_seconds=30
)

if success:
    print("StatefulSet 삭제 완료")
```

**주의:**
- StatefulSet을 삭제해도 **PVC는 자동으로 삭제되지 않음**
- 데이터를 완전히 제거하려면 PVC를 별도로 삭제해야 함

---

## 사용 시나리오

### 시나리오 1: MySQL 클러스터 배포

```python
# 1. Headless Service 생성 (먼저 필요)
# (Service Manager 사용)

# 2. StatefulSet 생성
mysql_sts = await manager.create_statefulset(
    name="mysql",
    namespace="database",
    service_name="mysql-headless",
    replicas=3,
    selector={"app": "mysql"},
    containers=[
        V1Container(
            name="mysql",
            image="mysql:8.0",
            ports=[{"containerPort": 3306}],
            env=[
                {"name": "MYSQL_ROOT_PASSWORD", "value": "secret"}
            ]
        )
    ],
    volume_claim_templates=[
        V1PersistentVolumeClaim(
            metadata={"name": "data"},
            spec={
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": "fast-ssd",
                "resources": {"requests": {"storage": "20Gi"}}
            }
        )
    ]
)

# 3. 준비 대기
is_ready = await manager.is_ready("mysql", "database")
while not is_ready:
    await asyncio.sleep(5)
    is_ready = await manager.is_ready("mysql", "database")

print("MySQL 클러스터 준비 완료")
```

### 시나리오 2: ZooKeeper 앙상블 배포

```python
zk_sts = await manager.create_statefulset(
    name="zookeeper",
    namespace="kafka",
    service_name="zk-headless",
    replicas=3,
    selector={"app": "zookeeper"},
    containers=[
        V1Container(
            name="zookeeper",
            image="zookeeper:3.8",
            ports=[
                {"containerPort": 2181, "name": "client"},
                {"containerPort": 2888, "name": "server"},
                {"containerPort": 3888, "name": "leader-election"}
            ],
            env=[
                {"name": "ZOO_SERVERS", 
                 "value": "server.1=zookeeper-0.zk-headless:2888:3888 "
                          "server.2=zookeeper-1.zk-headless:2888:3888 "
                          "server.3=zookeeper-2.zk-headless:2888:3888"}
            ]
        )
    ],
    volume_claim_templates=[
        V1PersistentVolumeClaim(
            metadata={"name": "data"},
            spec={
                "accessModes": ["ReadWriteOnce"],
                "resources": {"requests": {"storage": "10Gi"}}
            }
        )
    ]
)
```

### 시나리오 3: Rolling Update 수행

```python
# 1. 이미지 버전 업데이트 (StatefulSet spec.template 수정 필요)
# (kubernetes API를 직접 사용하거나 kubectl apply 사용)

# 2. 업데이트 상태 모니터링
while True:
    status = await manager.get_statefulset_status("mysql", "database")
    
    print(f"Current: {status['current_replicas']}, "
          f"Updated: {status['updated_replicas']}, "
          f"Ready: {status['ready_replicas']}")
    
    # 모든 Pod가 업데이트되고 준비되면 완료
    if (status['updated_replicas'] == status['replicas'] and
        status['ready_replicas'] == status['replicas']):
        print("Rolling Update 완료")
        break
    
    await asyncio.sleep(10)
```

---

## 모범 사례

### 1. Headless Service와 함께 사용

StatefulSet은 **반드시 Headless Service**와 함께 사용해야 합니다:

```yaml
# Headless Service (ClusterIP: None)
apiVersion: v1
kind: Service
metadata:
  name: mysql-headless
spec:
  clusterIP: None  # Headless
  selector:
    app: mysql
  ports:
    - port: 3306
```

각 Pod는 안정적인 DNS 이름을 가집니다:
- `mysql-0.mysql-headless.default.svc.cluster.local`
- `mysql-1.mysql-headless.default.svc.cluster.local`

### 2. PVC 관리 전략

```python
# 스케일 다운 후 PVC 정리 (선택적)
# 주의: 데이터가 영구 삭제됨!

# 1. StatefulSet 삭제
await manager.delete_statefulset("mysql", "database")

# 2. PVC 수동 삭제 (PVC Manager 사용)
pvcs = await pvc_manager.list_pvcs(
    namespace="database",
    label_selector="app=mysql"
)

for pvc in pvcs:
    await pvc_manager.delete_pvc(pvc.metadata.name, "database")
```

### 3. 순서 보장 활용

```python
# OrderedReady 정책: 데이터베이스 클러스터에 적합
# - master가 먼저 시작 (mysql-0)
# - replica가 순서대로 시작 (mysql-1, mysql-2)

sts = await manager.create_statefulset(
    name="mysql",
    namespace="database",
    service_name="mysql-headless",
    replicas=3,
    pod_management_policy="OrderedReady",  # 순서 보장
    ...
)
```

### 4. StatefulSet vs Deployment

| 기준 | StatefulSet | Deployment |
|------|-------------|------------|
| Pod 이름 | 예측 가능 (myapp-0, myapp-1) | 랜덤 (myapp-abc123) |
| 네트워크 ID | 안정적 (고정 DNS) | 불안정 (IP 변경 가능) |
| 스토리지 | 각 Pod가 독립적 PVC | 모든 Pod가 공유하거나 없음 |
| 생성/삭제 순서 | 순서 보장 | 순서 없음 (병렬) |
| 사용 사례 | Stateful 앱 (DB, 큐) | Stateless 앱 (웹서버, API) |

---

## 예외 처리

| 예외 클래스 | 발생 시점 | 처리 방법 |
|-----------|---------|---------|
| `StatefulSetCreationException` | StatefulSet 생성 실패 | Headless Service 존재 확인, RBAC 권한 확인 |
| `StatefulSetReadException` | StatefulSet 조회 실패 (404 제외) | 네임스페이스 확인, 네트워크 상태 확인 |
| `StatefulSetUpdateException` | StatefulSet 업데이트 실패 | Spec 유효성 확인, 리소스 제한 확인 |
| `StatefulSetDeletionException` | StatefulSet 삭제 실패 | Finalizer 확인, PVC 정책 확인 |
| `StatefulSetListException` | 목록 조회 실패 | RBAC 권한 확인, API 서버 상태 확인 |

```python
from infra.kubernetes.managers.statefulset.exceptions import (
    StatefulSetCreationException,
    StatefulSetUpdateException
)

try:
    sts = await manager.create_statefulset(
        name="mysql",
        namespace="database",
        service_name="mysql-headless",  # 존재하지 않으면 실패
        replicas=3,
        selector={"app": "mysql"},
        containers=[...]
    )
except StatefulSetCreationException as e:
    print(f"StatefulSet 생성 실패: {e.reason}")
    print(f"상세 정보: {e.detail}")
```

---

## 주의사항

### 1. PVC 자동 삭제되지 않음

```python
# ⚠️ StatefulSet 삭제 시 PVC는 남아있음
await manager.delete_statefulset("mysql", "database")
# → mysql-data-mysql-0, mysql-data-mysql-1 PVC는 여전히 존재
```

### 2. Headless Service 필수

```python
# ❌ 잘못된 예: Headless Service 없이 생성
await manager.create_statefulset(
    name="mysql",
    namespace="database",
    service_name="non-existent-service",  # 존재하지 않음
    ...
)
# → StatefulSet은 생성되지만 Pod DNS가 제대로 작동하지 않음
```

### 3. 스케일 다운 시 데이터 손실 위험

```python
# ⚠️ 스케일 다운: 마지막 Pod부터 삭제됨
await manager.scale_statefulset("mysql", "database", replicas=1)
# → mysql-2, mysql-1이 삭제됨
# → 해당 Pod의 데이터는 PVC에 남지만, Pod는 사라짐
```

---

## 관련 리소스

- **Service Manager**: Headless Service 생성
- **PVC Manager**: PersistentVolumeClaim 관리
- **ConfigMap Manager**: 설정 데이터 주입
- **Secret Manager**: 민감 데이터 관리

---

## 참고

- StatefulSet은 **상태를 유지하는 애플리케이션**을 위한 것입니다
- **Deployment**는 상태를 유지하지 않는 애플리케이션에 사용하세요
- RMS 원칙에 따라 **멱등성이 보장**됩니다
- 모든 작업은 **비동기(async/await)** 로 수행됩니다
