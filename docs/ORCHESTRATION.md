> **v0.3 갱신:** 아래 초기 설계 중 파일 중심 Feature Flow는 `docs/CYCLE_04_CONTRACT.md`로 대체합니다. 현재 계약은 schema 1.1: System Flow → API/SDK 본문 처리 단계 → 함수 내부/근거. 파일 그래프는 보조 보기입니다. 제품 파이프라인의 BUILD에서 `process.py`가 같은 근거 그래프에 본문 범위를 투영합니다. 단계 이름은 규칙 기반 해석, 선은 소스 읽기 순서, 호출 대상은 정적 후보입니다. 실제 실행/성공을 증명하지 않습니다. GitHub 수집 예산은 160파일(총 2 MiB)입니다.

# Skills와 orchestration

## 1. 개발하는 Codex의 흐름
CONTEXT → SPEC → CONTRACT → FAILING TEST → IMPLEMENT → VERIFY → REVIEW → HANDOFF
- 사람: 목적/범위/수용 기준, 배포·유료 호출·외부 쓰기 승인.
- Codex: 파일 조사, 최소 변경, 테스트 실행, 근거 제출.
- Orchestrator Skill: 적절한 작업 절차와 순서를 선택한다. 워커가 아니다.
- Evidence Reviewer Skill: 그래프/출처/한계 표기를 반대 관점에서 검사한다.
- skill-creator: 반복 실패의 재현 사례가 쌓인 뒤 개선 제안에만 사용한다. 자동 자기수정/무제한 Skill 생성 금지.

개발 작업은 이 MVP에서 순차 실행했다. 독립 subagent를 실행한 것으로 표현하지 않는다. 이후 UI와 parser를 병렬화할 때도 먼저 Pydantic/API 계약을 고정한다.

## 2. 앱 런타임의 실제 흐름
INTAKE → EXTRACT → BUILD → VERIFY → [EXPLAIN] → READY
모든 단계는 `StageRecord`로 입력/출력 개수·상태·시간·메시지를 남긴다.
- INTAKE: URL/파일 검증, commit 고정, 허용 텍스트만 수집.
- EXTRACT: import, API route, HTTP request, symbol, dependency facts.
- BUILD: canonical graph, system view, feature slices.
- VERIFY: ID/근거/부모/하위집합/누락 표시 검사. 오류면 결과 공개 중단.
- EXPLAIN: 사용자 opt-in + 서버 키/모델 설정 시 1회 호출. 실패면 warning 후 정적 결과 유지.
- READY: UI에서 전체 → 기능 → 근거. 요청을 몰래 재시도하지 않는다.

## 예산과 실패 정책
한 요청 최대 160 local source files / 48 remote files / 파일당 64 KiB / 총 2 MiB.
GitHub 동시 읽기 4, 앱 분석 동시 처리 2. 외부 요청 timeout과 전체 요청 timeout을 둔다.
빈 프로젝트, 지원 안 되는 언어, 비공개 저장소, 너무 큰 파일, GitHub rate limit은 명확히 보고한다.
LLM이 존재하지 않는 node/evidence ID를 내면 출력 전체를 무시한다.

## Skills 선정 원칙
기존 프레임워크 문서·browser verification 절차를 재사용한다. 프로젝트 고유 절차만 2개 Skill로 만든다.
- `.agents/skills/flowlens-orchestrator/SKILL.md`
- `.agents/skills/architecture-evidence-reviewer/SKILL.md`
이 파일들이 제품 서버에서 자동 실행되지는 않는다. 런타임 실행은 `app/orchestrator.py`가 책임진다.
