# Job Manager 가이드

## 개요

`JobManager`는 Kubernetes Job 리소스를 관리하는 클래스입니다. Job은 한 번 실행되어 완료되는 배치 작업을 관리하며, 성공적으로 완료될 때까지 Pod를 재시도합니다.

## 주요 기능

### 1. Job 생성 (`create_job`)
- **멱등성 보장**: 동일한 이름의 Job이 이미 존재하면 기존 리소스 반환
- **배치 작업 설정**: completions, parallelism, backoffLimit 등 지원
- **TTL 설정**: 완료 후 자동 삭제 시간 설정 가능

```python
from kubernetes_asyncio.client import V1Container

manager = JobManager(k8s_client)

# 컨테이너 정의
container = V1Container(
    name="batch-job",
    image="busybox:latest",
    command=["sh", "-c", "echo Processing... && sleep 10"]
)

# Job 생성
job = await manager.create_job(
    name="batch-process",
    namespace="production",
    containers=[container],
    completions=5,              # 5번 성공적으로 완료
    parallelism=2,              # 동시에 2개 실행
    backoff_limit=3,            # 최대 3번 재시도
    ttl_seconds_after_finished=3600,  # 완료 후 1시간 뒤 삭제
    restart_policy="Never"      # 또는 "OnFailure"
)
```

### 2. Job 조회 (`get_job`)

```python
job = await manager.get_job(
    name="batch-process",
    namespace="production"
)
```

### 3. Job 삭제 (`delete_job`)
- **전파 정책 설정**: Background, Foreground, Orphan
- Background (기본): Job 먼저 삭제, Pod는 백그라운드에서 삭제
- Foreground: Pod 먼저 삭제 후 Job 삭제
- Orphan: Job만 삭제, Pod는 유지

```python
success = await manager.delete_job(
    name="batch-process",
    namespace="production",
    propagation_policy="Foreground"
)
```

### 4. Job 상태 조회 (`get_job_status`)
- **active**: 실행 중인 Pod 수
- **succeeded**: 성공한 Pod 수
- **failed**: 실패한 Pod 수
- **completion_time**: 완료 시각
- **conditions**: 상태 조건

```python
status = await manager.get_job_status(
    name="batch-process",
    namespace="production"
)

if status:
    print(f"Active: {status['active']}")
    print(f"Succeeded: {status['succeeded']}")
    print(f"Failed: {status['failed']}")
```

### 5. Job 완료 여부 확인 (`is_complete`)

```python
if await manager.is_complete("batch-process", "production"):
    print("Job completed successfully")
```

### 6. Job 실패 여부 확인 (`is_failed`)

```python
if await manager.is_failed("batch-process", "production"):
    print("Job failed")
```

### 7. Job 목록 조회 (`list_jobs`)

```python
# 네임스페이스별 조회
jobs = await manager.list_jobs(namespace="production")

# 레이블 셀렉터로 필터링
jobs = await manager.list_jobs(
    namespace="production",
    label_selector="job-name=batch-process"
)
```

## Job 실행 전략

### 완료 모드 (completions)
- **None**: Pod가 성공하면 Job 완료
- **양수**: 지정된 횟수만큼 성공적으로 완료해야 함

### 병렬 실행 (parallelism)
- **None 또는 1**: 순차 실행
- **양수**: 동시에 실행할 최대 Pod 수

### 재시도 정책 (backoffLimit)
- **기본값**: 6
- 실패 시 재시도 횟수 제한
- 초과 시 Job 실패로 표시

### 시간 제한 (activeDeadlineSeconds)
- Job의 최대 실행 시간
- 초과 시 Job 종료 및 실패 표시

## 예제 시나리오

### 1. 단일 실행 Job
```python
# 한 번만 실행하고 완료
job = await manager.create_job(
    name="one-time-task",
    namespace="default",
    containers=[container],
    completions=1,
    parallelism=1
)
```

### 2. 병렬 배치 처리
```python
# 100개 작업을 10개씩 병렬 처리
job = await manager.create_job(
    name="parallel-batch",
    namespace="default",
    containers=[container],
    completions=100,
    parallelism=10,
    backoff_limit=5
)
```

### 3. 작업 큐 패턴
```python
# completions 없이 병렬 실행 (큐에서 작업 가져오기)
job = await manager.create_job(
    name="queue-worker",
    namespace="default",
    containers=[container],
    parallelism=5,
    # completions를 지정하지 않으면 Pod가 성공하면 완료
)
```

## 멱등성 보장

- 동일한 이름의 Job 재생성 시 기존 Job 반환
- 409 Conflict 발생 시 자동 재조회

## 예외 처리

| 예외 클래스 | 발생 시점 |
|-----------|----------|
| `JobCreationException` | Job 생성 실패 |
| `JobReadException` | Job 조회 실패 (404 제외) |
| `JobUpdateException` | Job 업데이트 실패 |
| `JobDeletionException` | Job 삭제 실패 |
| `JobListException` | Job 목록 조회 실패 |

## 주의사항

1. **재시작 정책**: "Never" 또는 "OnFailure"만 사용 가능 ("Always" 불가)
2. **Job 불변성**: 생성 후 spec 수정 불가 (삭제 후 재생성 필요)
3. **Pod 정리**: TTL 설정 또는 수동 삭제 필요
4. **실패 처리**: backoffLimit 초과 시 재실행 불가
5. **타임아웃**: activeDeadlineSeconds 설정 권장

## 관련 리소스

- **CronJob**: Job을 스케줄에 따라 자동 생성
- **Pod**: Job이 생성/관리
- **ConfigMap/Secret**: Job에 설정 주입
