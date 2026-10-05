# FlowLens 개선 계획

기준 버전: **v0.2.0**

## 이번 사이클에서 반영한 개선

### P0 · 입력 경로

- [x] 공개 GitHub 저장소 URL 분석 경로 유지
- [x] 로컬 폴더 분석
- [x] **ZIP 파일 직접 분석 추가**
- [x] ZIP을 디스크에 풀지 않는 read-only intake
- [x] ZIP path traversal / 암호화 / symlink / 파일 수 / 크기 제한
- [x] GitHub/ZIP 모두 같은 `analyze_snapshot()` 파이프라인 사용

### P0 · 검증

- [x] 64개 Python 테스트 통과
- [x] 실제 ZIP을 localhost HTTP API에 전송해 분석
- [x] 브라우저 bridge QA 12개 항목 통과
- [x] 실제 VibeCare GitHub tree와 기술 스택을 연결된 GitHub에서 확인
- [x] live GitHub 전용 수동 검사 스크립트 추가

## 다음 개선 우선순위

### P1 · GitHub 실제 사용성

1. live GitHub 재검증을 CI 또는 네트워크 허용 환경에서 수행
2. GitHub URL 입력 시 rate-limit/권한/부분 분석을 UI에서 더 명확히 구분
3. 기본 브랜치뿐 아니라 사용자가 branch/tag/commit을 선택할 수 있는 읽기 전용 옵션
4. 큰 저장소에서 48개 파일 단순 cutoff 대신 **architecture-relevance ranking** 적용

### P1 · System Flow 정확도

현재는 파일 경로·import·SDK 패턴으로 다음 역할을 압축한다.

```text
User
→ App
→ State / Controller
→ Service / HTTP
→ Backend
→ Infrastructure
```

다음 단계에서는 단순 파일 수가 아니라 다음 evidence를 합쳐 핵심 노드를 선택한다.

- entry point
- framework bootstrap
- route registration
- dependency direction
- API client
- persistence driver
- external SDK

목표: VibeCare에서 첫 화면이 자연스럽게 다음 수준으로 수렴하도록 한다.

```text
사용자
  ↓
Flutter App
  ↓
Riverpod / Controller
  ↓
Service / Dio
  ↓ HTTP
Hono Backend
  ├─ Auth
  ├─ FITRUS
  ├─ Algorithm
  ├─ Validation
  └─ Storage
       ↓
   PostgreSQL

+ Supabase
```

### P1 · Feature Flow 정확도

현재 기능 지도는 route 주변 **파일 단위 induced subgraph**다. 다음 개선은 다음 순서다.

1. route prefix 조합 (`/v1` + router path)
2. path parameter normalization (`:id`, `{id}`)
3. Dio/fetch/Axios request와 backend route의 contract matching
4. 함수 정의 → 직접 함수 호출 edge
5. controller → service → API client → route 순서의 evidence score

함수 호출을 완전히 증명하지 못하면 계속 `candidate`로 남긴다.

### P2 · 코드베이스 규모 대응

- tree-sitter 또는 언어별 parser 검토
- monorepo package boundary 인식
- framework adapter 분리: Flutter, React, Next.js, Hono, FastAPI, Spring
- Incremental cache: revision + path hash
- 분석 결과 diff: 이전 commit 대비 architecture 변화

### P2 · 제품 UX

- 노드 클릭 시 "왜 이 계층으로 분류했는지" 근거 표시
- System → Feature breadcrumb 강화
- 검색: 파일/함수/API 입력 시 관련 Feature Flow로 포커스
- 큰 그래프 자동 접기 및 `+N hidden` 표시
- 분석 신뢰도/누락 이유를 노드별로 표시

## 하지 않을 것

MVP 단계에서는 다음을 핵심 기능에 섞지 않는다.

- 코드를 자동 수정하는 Agent
- 대상 저장소 코드 실행
- 패키지 자동 설치
- 배포 자동화
- 보안 취약점 탐지 도구 전체 기능
- 모든 함수를 한 화면에 나열하는 그래프

FlowLens의 핵심은 **"코드를 많이 보여주는 것"이 아니라 "전체 실행 경로를 먼저 이해시키고, 필요한 기능만 깊게 보여주는 것"**이다.

## 다음 구현 사이클의 완료 기준

1. VibeCare live GitHub 분석 성공 캡처
2. System Flow가 Flutter → Riverpod/Controller → Dio → Hono → PostgreSQL/Supabase를 과도한 노드 없이 표현
3. 최소 3개 기능(Auth / Measurement / Recommendation)이 Feature Flow로 내려감
4. 각 Feature Flow가 실제 파일/줄 evidence를 제공
5. 잘못 연결된 edge를 confirmed로 승격하지 않음
6. 전체 자동 테스트 + browser smoke 재통과
