# CronJob Manager 가이드

## 개요

CronJob Manager는 **스케줄에 따라 반복적으로 실행되는 Job**을 관리하는 Kubernetes CronJob 리소스를 담당합니다.

CronJob의 핵심 특징:
- **Cron 표현식 기반 스케줄**: Unix cron과 동일한 문법 사용
- **자동 Job 생성**: 스케줄에 따라 Job이 자동으로 생성됨
- **실행 이력 관리**: 성공/실패한 Job을 자동으로 정리
- **동시성 제어**: 중복 실행 방지 또는 허용 정책 설정 가능

대표적인 사용 사례:
- **백업 작업**: 데이터베이스 백업, 파일 백업
- **배치 처리**: 일일 리포트 생성, 데이터 집계
- **정기 점검**: 시스템 헬스 체크, 로그 정리
- **데이터 동기화**: 외부 시스템과의 주기적 동기화

---

## 주요 기능

### 1. CronJob 생성 (멱등성 보장)

```python
from kubernetes_asyncio.client import V1Container

# 기본 CronJob 생성
cronjob = await manager.create_cronjob(
    name="daily-backup",
    namespace="operations",
    schedule="0 2 * * *",  # 매일 새벽 2시
    containers=[
        V1Container(
            name="backup",
            image="backup-tool:latest",
            command=["sh", "-c", "backup.sh"],
            env=[
                {"name": "BACKUP_TARGET", "value": "s3://my-bucket/backups"}
            ]
        )
    ],
    labels={"app": "backup", "type": "maintenance"},
    restart_policy="OnFailure"  # 실패 시 재시도
)

print(f"CronJob 생성됨: {cronjob.metadata.name}")
print(f"Schedule: {cronjob.spec.schedule}")
```

### 2. Cron 스케줄 표현식

```python
# Cron 표현식: 분 시 일 월 요일
# ┌─── 분 (0-59)
# │ ┌─── 시 (0-23)
# │ │ ┌─── 일 (1-31)
# │ │ │ ┌─── 월 (1-12)
# │ │ │ │ ┌─── 요일 (0-6, 0=일요일)
# │ │ │ │ │
# * * * * *

# 예시:
schedules = {
    "매 5분마다": "*/5 * * * *",
    "매시 정각": "0 * * * *",
    "매일 새벽 2시": "0 2 * * *",
    "매주 월요일 9시": "0 9 * * 1",
    "매월 1일 자정": "0 0 1 * *",
    "평일 오전 9시": "0 9 * * 1-5",
    "주말 제외 매일": "0 0 * * 0,6"
}

# 사용 예:
cronjob = await manager.create_cronjob(
    name="hourly-report",
    namespace="analytics",
    schedule="0 * * * *",  # 매시간 정각
    containers=[...]
)
```

### 3. 고급 옵션 설정

```python
# 완전한 옵션을 가진 CronJob
cronjob = await manager.create_cronjob(
    name="database-backup",
    namespace="database",
    schedule="0 2 * * *",
    containers=[
        V1Container(
            name="pg-dump",
            image="postgres:14",
            command=["pg_dump", "-h", "postgres", "-U", "admin", "mydb"]
        )
    ],
    labels={"app": "backup", "database": "postgres"},
    annotations={"description": "Daily PostgreSQL backup"},
    
    # 동시성 정책
    concurrency_policy="Forbid",  # 중복 실행 방지 (Allow, Forbid, Replace)
    
    # Job 이력 보관
    successful_jobs_history_limit=3,  # 성공한 Job 3개 보관
    failed_jobs_history_limit=1,      # 실패한 Job 1개 보관
    
    # 시작 데드라인
    starting_deadline_seconds=300,  # 5분 내에 시작해야 함
    
    # 일시 중지 여부
    suspend=False,  # False면 활성화, True면 중지
    
    # Pod 재시작 정책
    restart_policy="OnFailure"  # OnFailure 또는 Never
)
```

**Concurrency Policy:**
- `Allow`: 동시 실행 허용 (기본값)
- `Forbid`: 이전 Job이 실행 중이면 새 Job 생성 안 함
- `Replace`: 이전 Job을 취소하고 새 Job 생성

### 4. CronJob 조회

```python
# 단일 CronJob 조회
cj = await manager.get_cronjob("daily-backup", "operations")
if cj:
    print(f"CronJob: {cj.metadata.name}")
    print(f"Schedule: {cj.spec.schedule}")
    print(f"Suspended: {cj.spec.suspend}")
else:
    print("CronJob이 존재하지 않음")

# 존재 여부 확인
exists = await manager.exists("daily-backup", "operations")
```

### 5. CronJob 목록 조회

```python
# 특정 네임스페이스의 모든 CronJob
cronjobs = await manager.list_cronjobs(namespace="operations")

# 레이블 셀렉터로 필터링
backup_jobs = await manager.list_cronjobs(
    namespace="operations",
    label_selector="type=backup"
)

# 전체 클러스터의 CronJob
all_cronjobs = await manager.list_cronjobs()
```

### 6. CronJob 상태 조회

```python
status = await manager.get_cronjob_status("daily-backup", "operations")
if status:
    print(f"Active Jobs: {status['active']}")  # 현재 실행 중인 Job 목록
    print(f"Last Schedule Time: {status['last_schedule_time']}")
    print(f"Last Successful Time: {status['last_successful_time']}")
```

### 7. CronJob 일시 중지/재개

```python
# CronJob 일시 중지
suspended = await manager.suspend_cronjob(
    name="daily-backup",
    namespace="operations",
    suspend=True  # 중지
)
print(f"CronJob 중지됨: {suspended.spec.suspend}")

# CronJob 재개
resumed = await manager.suspend_cronjob(
    name="daily-backup",
    namespace="operations",
    suspend=False  # 재개
)
print(f"CronJob 재개됨: {not resumed.spec.suspend}")
```

### 8. 스케줄 변경

```python
# 실행 시간 변경
updated = await manager.update_schedule(
    name="daily-backup",
    namespace="operations",
    schedule="0 3 * * *"  # 새벽 2시 → 3시로 변경
)

print(f"새로운 스케줄: {updated.spec.schedule}")
```

### 9. 레이블 및 어노테이션 업데이트

```python
# 레이블 추가
updated = await manager.update_labels(
    name="daily-backup",
    namespace="operations",
    labels={"version": "v2", "environment": "production"},
    merge=True
)

# 어노테이션 추가
updated = await manager.update_annotations(
    name="daily-backup",
    namespace="operations",
    annotations={"last-modified-by": "admin"},
    merge=True
)
```

### 10. CronJob 삭제

```python
# CronJob 삭제 (생성된 Job은 남음)
success = await manager.delete_cronjob(
    name="daily-backup",
    namespace="operations"
)

if success:
    print("CronJob 삭제 완료")
```

---

## 사용 시나리오

### 시나리오 1: 데이터베이스 백업 (매일 새벽)

```python
# PostgreSQL 백업을 매일 새벽 2시에 실행
backup_job = await manager.create_cronjob(
    name="postgres-backup",
    namespace="database",
    schedule="0 2 * * *",  # 매일 02:00
    containers=[
        V1Container(
            name="backup",
            image="postgres:14-alpine",
            command=[
                "sh", "-c",
                "pg_dump -h postgres.database.svc -U $POSTGRES_USER $POSTGRES_DB | "
                "gzip > /backup/db-$(date +%Y%m%d-%H%M%S).sql.gz"
            ],
            env=[
                {"name": "POSTGRES_USER", "value": "admin"},
                {"name": "POSTGRES_DB", "value": "myapp"},
                {"name": "PGPASSWORD", "valueFrom": {"secretKeyRef": {"name": "pg-secret", "key": "password"}}}
            ],
            volume_mounts=[
                {"name": "backup-storage", "mountPath": "/backup"}
            ]
        )
    ],
    concurrency_policy="Forbid",  # 중복 실행 방지
    successful_jobs_history_limit=7,  # 7일치 백업 보관
    failed_jobs_history_limit=3,
    restart_policy="OnFailure"
)

print("PostgreSQL 백업 CronJob 생성 완료")
```

### 시나리오 2: 로그 정리 (매주 일요일)

```python
# 오래된 로그 파일 삭제 (매주 일요일 새벽 1시)
cleanup_job = await manager.create_cronjob(
    name="log-cleanup",
    namespace="logging",
    schedule="0 1 * * 0",  # 일요일 01:00
    containers=[
        V1Container(
            name="cleanup",
            image="busybox:latest",
            command=[
                "sh", "-c",
                "find /logs -type f -name '*.log' -mtime +30 -delete"
            ],
            volume_mounts=[
                {"name": "log-volume", "mountPath": "/logs"}
            ]
        )
    ],
    concurrency_policy="Replace",  # 이전 작업 취소하고 새 작업 시작
    successful_jobs_history_limit=4,  # 최근 4주 보관
    restart_policy="Never"
)
```

### 시나리오 3: API 헬스 체크 (매 10분)

```python
# 외부 API 상태 확인 (10분마다)
health_check = await manager.create_cronjob(
    name="api-health-check",
    namespace="monitoring",
    schedule="*/10 * * * *",  # 10분마다
    containers=[
        V1Container(
            name="curl",
            image="curlimages/curl:latest",
            command=[
                "sh", "-c",
                "curl -f https://api.example.com/health || exit 1"
            ]
        )
    ],
    concurrency_policy="Allow",  # 동시 실행 허용
    successful_jobs_history_limit=10,
    failed_jobs_history_limit=5,
    starting_deadline_seconds=60,  # 1분 내 시작
    restart_policy="Never"  # 실패 시 재시도 안 함
)
```

### 시나리오 4: 스케줄 동적 변경

```python
# 운영 중 스케줄 변경 (예: 새벽 2시 → 3시)
print("현재 스케줄 확인...")
cj = await manager.get_cronjob("postgres-backup", "database")
print(f"기존 스케줄: {cj.spec.schedule}")

# 스케줄 변경
print("스케줄 변경 중...")
updated = await manager.update_schedule(
    name="postgres-backup",
    namespace="database",
    schedule="0 3 * * *"  # 새벽 3시로 변경
)
print(f"새로운 스케줄: {updated.spec.schedule}")
```

### 시나리오 5: 일시 중지 후 재개

```python
# 유지보수 기간 동안 백업 중지
print("백업 작업 일시 중지...")
await manager.suspend_cronjob(
    name="postgres-backup",
    namespace="database",
    suspend=True
)

# ... 유지보수 작업 ...

# 백업 재개
print("백업 작업 재개...")
await manager.suspend_cronjob(
    name="postgres-backup",
    namespace="database",
    suspend=False
)
```

---

## 모범 사례

### 1. Idempotency (멱등성) 보장

CronJob은 여러 번 실행될 수 있으므로 **작업이 멱등적**이어야 합니다:

```python
# ✅ 좋은 예: 멱등적 작업
containers=[
    V1Container(
        name="sync",
        image="rclone:latest",
        command=["rclone", "sync", "source:", "dest:", "--update"]
        # sync는 멱등적: 여러 번 실행해도 결과 동일
    )
]

# ❌ 나쁜 예: 비멱등적 작업
containers=[
    V1Container(
        name="append",
        image="busybox",
        command=["sh", "-c", "echo 'data' >> /output/file.txt"]
        # 매번 중복 데이터가 추가됨
    )
]
```

### 2. 리소스 제한 설정

```python
containers=[
    V1Container(
        name="backup",
        image="backup-tool:latest",
        resources={
            "limits": {"memory": "1Gi", "cpu": "500m"},
            "requests": {"memory": "512Mi", "cpu": "200m"}
        }
    )
]
```

### 3. Job 이력 관리

```python
# 디스크 공간 절약을 위해 이력 제한
successful_jobs_history_limit=3,  # 최근 3개만 보관
failed_jobs_history_limit=1,      # 최근 1개만 보관
```

### 4. Concurrency Policy 선택

| 정책 | 사용 사례 |
|------|---------|
| `Forbid` | 데이터베이스 백업 (중복 실행 방지) |
| `Replace` | 시스템 정리 작업 (최신 작업만 필요) |
| `Allow` | 독립적인 헬스 체크 (동시 실행 무방) |

```python
# 백업은 Forbid 권장
concurrency_policy="Forbid"  # 이전 백업이 완료될 때까지 대기
```

### 5. Timezone 고려

Kubernetes CronJob은 **kube-controller-manager의 타임존**을 사용합니다:
- 클러스터 타임존 확인 필요
- UTC 기준으로 스케줄 작성 권장

```python
# UTC 기준 스케줄 작성 (권장)
schedule="0 14 * * *",  # UTC 14:00 = KST 23:00 (KST = UTC+9)
```

---

## 예외 처리

| 예외 클래스 | 발생 시점 | 처리 방법 |
|-----------|---------|---------|
| `CronJobCreationException` | CronJob 생성 실패 | 스케줄 표현식 유효성 확인, RBAC 권한 확인 |
| `CronJobReadException` | CronJob 조회 실패 (404 제외) | 네임스페이스 확인, API 서버 상태 확인 |
| `CronJobUpdateException` | CronJob 업데이트 실패 | Spec 유효성 확인, 스케줄 문법 확인 |
| `CronJobDeletionException` | CronJob 삭제 실패 | Finalizer 확인, 생성된 Job 상태 확인 |
| `CronJobListException` | 목록 조회 실패 | RBAC 권한 확인, 네트워크 상태 확인 |

```python
from src.infra.kubernetes.managers.cronjob.exceptions import (
    CronJobCreationException,
    CronJobUpdateException
)

try:
    cj = await manager.create_cronjob(
        name="backup",
        namespace="default",
        schedule="invalid schedule",  # 잘못된 스케줄
        containers=[...]
    )
except CronJobCreationException as e:
    print(f"CronJob 생성 실패: {e.reason}")
    print(f"상세 정보: {e.detail}")
```

---

## 주의사항

### 1. 스케줄 중복 실행 가능

```python
# ⚠️ 작업이 오래 걸리면 다음 스케줄과 겹칠 수 있음
schedule="*/5 * * * *",  # 5분마다
# 작업이 10분 걸리면? → 중복 실행 발생 가능

# 해결: Forbid 정책 사용
concurrency_policy="Forbid"
```

### 2. Timezone 주의

```python
# ❌ 잘못된 예: 로컬 타임존 가정
schedule="0 23 * * *",  # 이것이 KST 23:00인지 UTC 23:00인지?

# ✅ 올바른 예: UTC 기준 명시
schedule="0 14 * * *",  # UTC 14:00 (명확히 UTC 기준)
# 주석에 로컬 시간 표기: KST 23:00
```

### 3. Job은 자동 삭제 안 됨

```python
# CronJob 삭제 시 생성된 Job은 남아있음
await manager.delete_cronjob("backup", "default")
# → backup-xxxxx Job들은 여전히 존재

# Job도 정리하려면 별도로 삭제 필요 (Job Manager 사용)
```

---

## CronJob vs Job

| 기준 | CronJob | Job |
|------|---------|-----|
| 실행 방식 | 스케줄 기반 자동 실행 | 수동 실행 (1회성) |
| 반복 여부 | 반복 실행 | 1회 실행 |
| 사용 사례 | 백업, 배치, 정기 작업 | 일회성 작업, 마이그레이션 |
| 이력 관리 | 자동 정리 가능 | 수동 정리 필요 |

---

## 관련 리소스

- **Job Manager**: CronJob이 생성한 Job 관리
- **ConfigMap Manager**: 스케줄 설정 외부화
- **Secret Manager**: 백업 자격 증명 관리

---

## 참고

- CronJob은 **정기적인 배치 작업**에 사용됩니다
- **Job**은 1회성 작업에 사용하세요
- RMS 원칙에 따라 **멱등성이 보장**됩니다
- 모든 작업은 **비동기(async/await)** 로 수행됩니다
- 스케줄은 **UTC 기준**으로 작성하는 것을 권장합니다
