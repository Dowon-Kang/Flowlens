# Codex 인계

## 현재 버전에서 지킬 것
전체 실행 경로를 먼저 보여주고, 기능별 상세 지도를 같은 graph에서 펼친다. 증거는 옆에 표시한다. Change Impact, 장애 시뮬레이션, 보안 점수, Wiki, 아이디어 추천으로 범위를 넓히지 않는다.

## 시작 프롬프트

```text
$flowlens-orchestrator

먼저 AGENTS.md, docs/PROJECT.md, docs/ARCHITECTURE.md,
docs/ORCHESTRATION.md, docs/CONTRACTS.md, docs/VERIFICATION.md를 읽어줘.
현재는 System Flow → Feature Flow → Evidence 로컬 MVP다.

코드를 바꾸기 전에 기존 테스트를 실행하고 현재 구조를 확인해줘.
이번 목표는 실제 저장소에서 발견한 누락 하나를 재현 테스트로 만들고,
두 지도의 공통 사실 그래프를 유지하며 가장 작은 수정으로 해결하는 것이다.

Python/JS/TS/Dart의 제한된 추출을 완전한 실행 추적으로 표현하지 말고,
확인된 정적 근거와 연결 후보·미지원 영역을 그대로 구분해줘.
기능별 상세 내용은 항상 System Flow의 부모 구성요소에 연결되어야 한다.

수정 후 architecture-evidence-reviewer 절차를 적용하고,
단위 테스트·Skills 검사·JS 구문 검사·브라우저 사용자 흐름을 실행해줘.
실행하지 못한 검증은 이유와 함께 미검증으로 남겨줘.
새 Skill/의존성/유료 호출/배포/저장소 push는 먼저 제안하고 승인 전 실행하지 마.
```

Skill이 자동 발견되지 않는 환경에서는 해당 `SKILL.md` 파일을 직접 읽도록 요청해도 된다. 이 안내가 사용자의 Codex 설정을 자동 변경한 것은 아니다.

## 다음 작업 우선순위
1. 실제 VibeCare 로컬 복사본을 입력해 System/Feature 결과를 사람이 확인하고, 잘못 묶인 사례를 작은 익명 fixture로 분리한다. 원본 소스를 불필요하게 공개하지 않는다.
2. 가장 잦은 실패 유형 하나부터 route mount/prefix 또는 Dart package/TS alias resolution으로 개선한다. 테스트 없이 범용 AST/LSP 엔진으로 대규모 교체하지 않는다.
3. 코드 근거를 통과한 기능에 한해 function-call 연결을 도입한다. 단순 파일 import 화살표를 함수 호출이라고 이름만 바꾸지 않는다.
4. 사용자가 AI 호출을 승인한 뒤 실제 모델로 설명 품질·근거 적합성을 평가한다. 설명 개선과 그래프 정확도 개선을 별도 지표로 본다.

외부 API 수집과 모델은 mock 계약 테스트까지 확인했다. 실제 GitHub/OpenAI 통합과 정상 브라우저 HTTP 테스트를 마친 뒤에만 행사 시연용 실연동으로 표시한다.
