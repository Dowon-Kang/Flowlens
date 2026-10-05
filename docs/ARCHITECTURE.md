# 아키텍처 결정서

## 하나의 사실 모델, 두 개의 지도
Repository snapshot → Facts → Canonical file graph
                             ├ System projection (역할/기술 계층으로 축약)
                             └ Feature projection (API endpoint 주변 부분 그래프)
두 그림을 LLM이 따로 생성하지 않는다. Feature의 파일 노드는 `component_id`로 System 노드에 연결된다.

## 실행 구조
Browser (HTML/CSS/ES modules + SVG)
  → FastAPI /api/analyze
  → bounded source intake
  → static fact extractor
  → graph builder / projector
  → independent structural verifier
  → optional AI explanation (existing IDs only)
  → JSON response → interactive diagrams + evidence pane

## ADR-001: agent swarm 대신 작은 파이프라인
추출·검증은 결정론적 함수로 한다. 병렬화는 제한된 파일 읽기만 허용한다. 다수 LLM이 동시에 동일 저장소를 해석하는 구조는 불일치와 비용을 늘릴 수 있으므로 채택하지 않는다.

## ADR-002: UI/서버 최소 스택
Python 3.11+ / FastAPI / Pydantic / HTTPX + 무빌드 ES modules / SVG.
Next.js/React Flow도 검토했으나 첫 버전에는 별도 Node 의존성 설치 없이 검증 가능한 작은 스택을 선택했다. UI는 API 계약을 유지하면 추후 React로 교체 가능하다.

## ADR-003: 정적 그래프를 runtime trace로 과장하지 않음
`confirmed`는 소스에 정적 관계/패턴이 존재함을 뜻한다. 실제 호출 성공·배포 상태·동적 실행 순서는 증명하지 않는다. `candidate`는 문맥/HTTP 계약 연결 추정이다.
JS/TS/Dart는 AST 전체 의미 분석이 아닌 lexical adapter다. Python은 stdlib ast로 추출하지만 동적 디스패치/DI/monkey patch는 미지원이다.

## ADR-004: 인프라 중복
Supabase SDK가 있으면 하나의 인프라 노드로 표시한다. PostgreSQL 드라이버가 별도로 발견되면 다른 클라이언트 노드로 유지하되, 같은 DB인지 다른 DB인지 배포 근거 없이 결론내리지 않는다. SQL 파일만으로 별도 운영 DB를 만들지 않는다.

## ADR-005: 공개 저장소만, 읽기 전용
GitHub host allowlist, commit-pinned tree/blobs, 파일/전체 크기 제한, redirect 금지, 요청 제한. 로컬 폴더도 선택한 파일 본문만 전달하고 파일시스템 경로로 서버 파일을 읽지 않는다.

## ADR-006: AI는 설명 전용
OpenAI Responses API structured output으로 기존 ID에 대한 설명만 받는다. 원시 파일 전체가 아닌 선택된 근거만 사용자 동의하에 전달한다. 출력은 비신뢰 데이터로 검증하며 사실 그래프는 바꾸지 않는다.

## 확장 경계
1. lexical adapter → Tree-sitter/LSP, alias resolver 개선.
2. 함수 단위 call graph와 HTTP origin 검증.
3. async jobs / persistent cache / private repo OAuth는 별도 범위 승인 후.
