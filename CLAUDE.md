M-ADP Resource Manager Server
1. 서비스 개요 (Overview)

M-ADP Resource Manager Server(RMS) 는
M-ADP 플랫폼 내의 여러 내부 서비스들이 공통으로 사용하는 Kubernetes 리소스 제어 전용 컨트롤 플레인이다.

이 서버의 목적은 Kubernetes API를 단순히 감싸는 것이 아니라,

Kubernetes 리소스 생성·변경·삭제를
“정책과 순서, 실패 처리를 포함한 의미 단위 작업”으로 제공하는 것

이다.

2. 왜 필요한가 (Problem)

Kubernetes는 리소스 간 강한 순서 의존성이 있다
(Namespace → SA → RBAC → Workload 등)

API 호출은 언제든 실패할 수 있고, 부분 성공이 발생한다

Vault 연동, RBAC 최소 권한, 네이밍 규칙 등은
호출자마다 직접 구현하면 일관성이 깨진다

내부 서비스가 Kubernetes의 모든 세부사항을 알면
→ 플랫폼 복잡도가 전파된다

👉 RMS는 이 복잡도를 중앙에서 흡수하기 위해 존재한다.

3. 서비스의 성격 (What this service is / is not)
RMS는 이것이다 ⭕

Kubernetes 리소스 관리 전문 서버

정책·순서·권한·실패 처리를 책임지는 오케스트레이터

“리소스 CRUD” + “묶음(오퍼레이션) API”를 모두 제공

RMS는 이것이 아니다 ❌

학생/최종 사용자용 API 서버

kubectl API Proxy

클러스터 운영 도구 (Node, PV, CRD 관리 ❌)

4. 관리 대상 리소스 (Scope)
직접 생성·관리하는 리소스

Namespace

ServiceAccount

Role / RoleBinding (Namespace scope)

ConfigMap

Deployment

StatefulSet

DaemonSet

ReplicaSet

Job

CronJob

PersistentVolumeClaim

Service

LimitRange

ResourceQuota

Vault 전제하에서의 Secret 처리

Kubernetes Secret 리소스는 생성하지 않는다

대신 다음을 관리한다:

ServiceAccount ↔ Vault Role 연결 구조

Workload(Deployment/StatefulSet/DaemonSet/CronJob)에 Vault 연동 설정 주입

즉, Secret 값이 아닌 “Secret 접근 구조”만 관리

관리하지 않는 리소스 (명시적 제외)

Pod (생성 ❌, 조회/관찰 ⭕)

Node

PersistentVolume / StorageClass

ClusterRole / CRD / AdmissionWebhook

5. API 설계 원칙

RMS의 API는 두 계층으로 구성된다.

5.1 Low-level Resource API (리소스 단위)

“이 Kubernetes 리소스를 생성/갱신/삭제한다”

예:

Namespace 생성

ServiceAccount 생성

Deployment 생성

Service 생성

특징:

내부 구현 및 테스트용

재사용 가능한 빌딩 블록

직접 사용은 제한적

5.2 High-level Bundle / Operation API (묶음 API, 핵심)

“의미 있는 작업을 RM이 책임지고 끝까지 수행한다”

예:

Application Environment Provision

Application Deployment

Environment Teardown

한 번의 호출로 내부에서:

Namespace 생성 (idempotent)

ServiceAccount 생성

Role / RoleBinding 연결

ConfigMap 적용

Deployment/StatefulSet/DaemonSet/CronJob 생성 또는 갱신

Vault 접근 구조 연결

👉 순서, 실패 처리, 정책 강제는 전부 RMS 책임

6. 묶음 API가 반드시 가져야 할 성질

Idempotency
동일 요청 N번 호출해도 결과는 항상 동일

순서 보장
호출자는 “무엇을”만 말하고 “어떻게”는 RMS가 결정

부분 실패 대응
롤백 / 재시도 / 상태 기록 중 하나 이상 필수

정책 강제
네이밍, 권한, 템플릿 제약을 RMS가 통제

관찰 가능성
현재 상태, 실패 지점, 이벤트 조회 가능

7. 아키텍처 관점 정리

RMS는 Kubernetes API의 현실(실패·권한·네트워크) 을 내부로 격리한다

호출자는 Kubernetes를 몰라도 된다

RMS는 “리소스 생성기”가 아니라
“플랫폼 정책 실행기” 다

8. 한 줄 요약

M-ADP Resource Manager Server는
Kubernetes 리소스를 직접 노출하지 않고,
정책·순서·실패 처리를 포함한
‘묶음 단위 오퍼레이션’을 제공하는 내부 컨트롤 플레인이다.