# FlowLens v0.4.0 — Cycle 07 실행·수정·검증

## 범위와 기준

원격 기준: `Dowon-Kang/Flowlens`, main `2cfc82bd33f41588182362ed8d0c6b6383db9278`.
작업 입력: 대화의 `FlowLens_MVP_v0.3.2_Local.zip`. 원격 v0.3.0의 핵심 파일 12개 blob SHA가 v0.3.0 원본 ZIP과 같음을 확인했다. 미반영된 Cycle05/06 신뢰도 수정과 테스트를 포함한다.

사용자는 UML 적용과 검증·수정 루프 이후 커밋/푸시를 승인했다. 대상 저장소 코드는 데이터로만 파싱했고 실행하지 않았다. 유료 AI, 배포, 프레임워크/의존성/워크플로 변경, 브라우저 보안 우회는 없다.

## 구현

- System → Process → Code 탐색과 기존 소스 읽기 순서 요약을 보존했다.
- 추가한 `활동 흐름 (UML)` 탭에서 지원 본문의 if/elif/else, guard, merge, return, raise/throw를 구분한다.
- 정상/예외 종료는 후속 정상 작업으로 연결되지 않는다. 양쪽 분기가 종료되면 거짓 합류를 만들지 않는다. 도달 불가 원문은 기존 소스 보기에서 확인할 수 있다.
- `ProcessFlow.activity`는 같은 flow/file/step/evidence ID에 연결된 투영이다. 독립적으로 상상한 그래프가 아니다. 새 노드의 정확한 문자 범위와 기존 CallSite 위치로 함수 참조를 연결한다.
- 포함은 기존 component/member, 구성 관계는 `Edge.relationship_kind`, 호출은 `CallSite.relation=call`, 활동 연결은 `control-flow`로 구분한다.
- UML-informed 부분 모델이며 전체 UML/XMI 준수 또는 시퀀스/클래스 다이어그램 구현을 주장하지 않는다. 제어 흐름 선은 실선이고 불확실성은 별도 표기다.
- JSON/SVG/Markdown에 활동 모델, guard, 미지원 이유, 실행 미검증 설명을 보존한다. 기존 저장 결과에서 activity가 없으면 재분석 안내를 표시한다.

## 지원과 한계

Python AST: 단순 문장, if/elif/else, return, raise. 루프, try/finally, with, match, yield, comprehension/지연 실행 등은 본문 전체의 활동 투영을 중단하고 원본 보기로 돌린다.

JS/TS/Dart: 균형 괄호와 명시적 세미콜론에 기반한 좁은 부분 문법이다. if/else의 블록·단문, return/throw를 다루며, 모호한 ASI·중첩 콜백·템플릿·반복·예외 처리 등은 이유를 남긴다. 컴파일러 수준 분석이 아니다.

표현식은 불투명한 작업이다. 암묵적 예외, 호출 내부, 단락 평가, 비동기 스케줄링, 조건의 실행 가능성은 증명하지 않는다. 정적 후보/미확인/실제 실행 미검증을 계속 구분한다. 128 활동 노드·24 중첩 깊이 상한에 도달하면 부분 체인을 정상 모델로 공개하지 않는다.

## 실패 → 수정 루프

1. 새 활동 계약 테스트 27개가 v0.3.2에서 실패했다. 조건별 분기와 종료, provenance gate, fallback을 구현했다.
2. 새 화면 helper 검사 2개가 실패했다. 기존 SVG 화면에 활동 탭·guard·코드 근거와 내보내기를 추가했다.
3. 추가 검토에서 조건식 내부 yield/comprehension과 JS의 세미콜론 없는 줄바꿈 3개를 재현했다. 미지원 표현식을 명시적으로 거부하도록 수정했다.
4. 같은 줄의 조건문과 분기 내부 호출이 섞이지 않도록 CallSite offset과 ActivityCallRef를 추가했다. 관계 유형 위조 검사도 추가했다.
5. 마지막 gate 검토에서 같은 줄의 다른 분기 참조를 위조하면 통과하던 실패 1개를 재현하고, 문자 범위까지 검사하도록 고쳤다.
6. 최종 전체 테스트와 실제 HTTP 입력 비교를 다시 실행했다. 테스트를 삭제하거나 assertion을 완화하지 않았다. 기존 브라우저 검사 내 schema assertion만 새 계약 1.2로 갱신하고 UML 조작 검사를 추가했다.

## 이번 실제 결과 (로컬, 새 실행)

| 명령/검사 | 결과 |
|---|---|
| 수정 전 pytest | 162 passed |
| 최종 `python -m pytest -q` | 199 passed (기존 162 + 신규 37) |
| `node --check static/app.js` | exit 0 |
| `python scripts/check_skills.py` | 두 Skill PASS, exit 0 |
| `python scripts/check_uml_http.py --output evidence/cycle-07/http` | 실제 localhost HTTP 6개 기준 PASS |
| 저장된 VibeCare source에 acceptance_flow.py 새 실행 | 7개 의미 기준 PASS |
| `python scripts/verify.py --browser --output evidence/cycle-07/verification` | 전체 exit 1: unit/skills/JS/http-zip PASS, browser launch FAIL |

현재 브라우저 실패는 Playwright가 요구하는 `chromium_headless_shell-1200` 실행 파일 부재다. 과거 관리자 차단을 이번 실패 이유로 재사용하지 않는다. 시스템 Chromium 재시도, 설치, bridge, 메모리 로드, 정책 변경으로 우회하지 않았다. Node SVG helper 검사는 실제 브라우저 검사가 아니다.

`git ls-remote`는 로컬 DNS에서 github.com을 해석하지 못했다. 원격 조회/쓰기에는 사용자가 연결한 GitHub 도구를 사용한다. 권한 설정이나 네트워크 정책을 바꾸지 않았다.

### 입력 일관성

실제 HTTP에서 helper 160개 뒤의 161번째 app/main.py와 제외 파일을 포함한 163개 집합으로 검사했다. 양쪽 모두 분석 160 / 정책 제외 2 / 개수 제한 1 / 읽기 실패 0, 진입점 선택 성공. 폴더/ZIP의 revision, canonical graph, 처리 지도, 활동 모델, evidence, quality/diagnostics가 같았다. 입력 종류와 browser 보고 필드까지 동일하다는 뜻은 아니다. 160파일/64KiB/2MiB/ZIP12MiB와 비밀 파일 제외를 유지했다.

### 실제 소스 적용 범위

고정 VibeCare commit `69307b9015f420803a132048ee98031c322d3cc1`의 저장된 74개 소스를 이번 코드로 다시 분석했다. 새 live GitHub 수집이나 과거 분석 JSON 재생은 아니다.

기존 11개 기능/45개 처리 지도는 유지됐다. **22개는 활동 부분 모델을 생성했고, 23개는 미지원 이유를 남겼다.** 예: Health, 세션 갱신, skeletalMuscleLevel, applyRequestedIntensity는 지원된다. calculateRecommendation과 추천 authorize API는 복잡한 콜백/예외 처리 등을 포함하므로 아직 기존 보기로 남는다. 이 한계를 숨기거나 전체 VibeCare UML 변환 완료로 표현하지 않는다.

## 주요 변경 파일

UML: `app/activity.py`(신규), `models.py`, `process.py`, `graph.py`, `verifier.py`, `static/app.js`, `tests/test_uml_activity.py`, `tests/uml_view.cjs`, `scripts/check_uml_http.py`, `scripts/browser_smoke.py`, README/CHANGELOG/Cycle07 문서, 버전.

원격에 함께 반영할 기존 로컬 수정: `http_clients.py`, `python_symbols.py`, `quality.py`, `intake.py`, `extractor.py`, `flow_scanner.py`, `main.py`, `orchestrator.py`, Cycle05/06 tests/docs. 이 내용의 과거 PASS는 이번 199개 검사와 혼동하지 않는다.

## 재현

```bash
python -m pytest -q
node --check static/app.js
python scripts/check_skills.py
python scripts/check_uml_http.py
python scripts/verify.py --browser
```

승인된 push 이후 기존 Actions가 실행되면 그 결과는 별도 기록한다. 로컬 browser FAIL을 원격 PASS로 덮어쓰지 않는다. 미실행 항목은 통과로 간주하지 않는다.
