# FlowLens

> **v0.4.0 · UML 활동 흐름:** 기존 구조와 v0.3.1/0.3.2의 신뢰도 수정을 유지하고, 지원하는 본문에 조건·조기 반환·명시적 예외를 구분하는 활동 보기를 추가했습니다. 기능 선택 후 **활동 흐름 (UML)** 탭을 사용하세요. 미지원 문법은 기존 소스 순서 보기로 남깁니다. 이번 로컬 검사 **199개 테스트·JS·Skills·실제 HTTP 폴더/ZIP 비교**는 통과했으나, 일반 브라우저는 실행 파일 부재로 미완료입니다. [현재 실행·제한 기록](docs/CYCLE_07_EXECUTION.md), [구현 전 계약](docs/CYCLE_07_UML_CONTRACT.md)을 확인하세요. 과거 PASS는 이번 검사 결과가 아닙니다.

**전체 시스템 → 기능 처리 단계 → 함수 내부 → 실제 코드 근거**를 탐색하는 로컬 분석기입니다. 여러 보기는 하나의 소스·근거 그래프를 서로 다른 관점으로 보여줍니다. 대상 코드를 실행해 관측한 runtime trace는 아닙니다.

## Windows에서 실행

Python 3.11 이상이 필요합니다. PowerShell:

```powershell
git clone https://github.com/Dowon-Kang/Flowlens.git
cd Flowlens
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다. ZIP으로 받은 경우 `run.py`가 있는 폴더에서 실행합니다. Activate.ps1이나 npm 설치는 앱 실행에 필요하지 않습니다. Linux/macOS는 `.venv/bin/python`을 사용합니다.

**localhost 전용 개발 도구입니다. 인증 없이 인터넷에 공개하지 마세요.**

## 사용

상단에서 공개 GitHub 저장소 URL, ZIP 파일 또는 로컬 폴더를 선택합니다. 먼저 기술 계층별 System Flow가 나타납니다. 기능 카드를 고르면 API/SDK 진입점별 처리 단계가 먼저 나타납니다. 최대 8개 묶음으로 보고 전체 단계를 펼칠 수 있습니다. 단계 클릭 → 실제 근거 → 연결 가능한 함수 내부로 내려갑니다. 파일 의존성은 별도의 `파일 참고도`입니다. PIN·refresh와 SDK 직접 인증은 다른 진입점으로 표시합니다. JSON / SVG / Markdown 내보내기를 지원합니다.

FlowCare와 TaskBoard는 합성 분석 예제입니다. 실제 VibeCare나 실행 가능한 제품으로 취급하지 마세요. `python scripts/build_offline_demo.py`로 생성하는 `demo.html`은 예제 탐색 전용이며 새 저장소 분석에는 서버가 필요합니다.

## 검증·수정 루프

검사에는 Node.js 22와 개발 의존성이 추가로 필요합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts/verify.py --browser
```

`verify.py`가 서버를 시작하고 종료합니다. 테스트, Skill, JS 구문, 실제 HTTP ZIP, 브라우저 결과를 `evidence/latest/EXECUTION_VALIDATION.md`, `report.json`, 개별 로그에 기록합니다.

실제 GitHub와 같은 커밋의 ZIP까지 검사하려면:

```powershell
.\.venv\Scripts\python.exe scripts/verify.py --browser --live https://github.com/Dowon-Kang/vibecare-pilot
```

요청 제한에 걸릴 때만 서버 환경변수 `GITHUB_TOKEN`을 설정합니다. 토큰을 Git에 올리지 마세요. GitHub Actions는 일반 브라우저 검증과 실제 GitHub/ZIP 검증을 분리하고 결과를 아티팩트에 보관합니다. **자동 검사는 코드를 자동 수정하지 않습니다.** 실패 로그 → 회귀 테스트 → 최소 수정 → 재검증 → Markdown 기록 순서로 개선합니다.

## UML 활동 보기

`if/elif/else`의 참·거짓 guard와 살아남은 경로의 합류, `return`의 정상 종료, `raise/throw`의 예외 전파 종료를 구분합니다. 기존 처리 단계는 소스 읽기 순서이고, 새 활동 보기만 제한된 제어 흐름 모델입니다. 포함은 기존 component/member 관계, 의존은 `Edge.relationship_kind`, 호출은 `CallSite.relation`, 제어 흐름은 `ProcessFlow.activity`로 분리하며 모두 같은 evidence ID를 사용합니다.

Python은 AST의 지원 문법만, JS/TS/Dart는 명시적 세미콜론과 균형 괄호로 확인한 부분 문법만 처리합니다. `try/finally`, 반복문, 모호한 ASI, 콜백/지연 실행 등은 활동 보기 미지원 사유를 남깁니다. 원본 보기와 함수 내부 탐색은 유지합니다. 표현식 내부의 단락 평가·암묵적 예외·비동기 스케줄링은 미모델링이며 실제 실행을 보장하지 않습니다.

UML의 decision/merge/control-flow 관점을 차용한 부분 구현입니다. UML 전체 준수·XMI·시퀀스/클래스 다이어그램 구현을 주장하지 않습니다. 활동 선은 실선, guard는 `[true]`/`[false]`, 신뢰도는 별도 배지입니다. 기존 SVG/JSON/Markdown으로 내보낼 수 있고 미지원 이유도 보존합니다.

## 구현 범위

Python AST와 JS/TS/Dart의 제한된 패턴을 분석합니다. 본문 범위를 분석한 처리 지도와 파일 단위 참고도를 제공합니다. 완전한 제어 흐름·함수 호출 그래프는 아닙니다. 단계명은 식별자·문장 형태에 근거한 규칙 기반 해석이며 AI의 검증된 업무 지식이 아닙니다. 단계 사이 화살표는 **소스 읽기 순서**이며, 분기·반복·조기 반환 때문에 실제 실행 순서와 다를 수 있습니다. 명시적 import/로컬 함수로 연결한 호출도 `정적 후보`입니다. 실선은 정적 소스 관계, HTTP 점선은 method/path 일치 후보입니다. 동적 URL·라우트 prefix·DI·실행 성공을 완전히 해석하지 않습니다.

GitHub는 커밋을 고정하고 폴더/ZIP과 같은 메타데이터 계획을 blob 다운로드 전에 적용합니다. GitHub/ZIP/폴더 모두 최대 160파일, 파일당 64 KiB, 총 2 MiB입니다. ZIP은 12 MiB, 내부 항목은 2,500개까지 받으며 압축 해제 전에 읽기 예산을 적용합니다. 문서·테스트·빌드 결과·비밀 파일은 제외합니다. 제한·생략·실패는 결과에 표시합니다.

폴더 선택은 경로·크기 목록을 `/api/file-plan`에 보내 ZIP과 같은 지원·제외·우선순위 정책을 적용한 후 선택된 내용만 읽습니다. 제외 파일의 내용은 보내지 않습니다. 분석 범위 화면과 JSON의 `coverage.reason_counts`, `coverage.browser_selection`에서 수·사유를 확인할 수 있습니다. 브라우저 보고 목록은 로컬 디스크 전체를 서버가 직접 검증했다는 뜻이 아닙니다.

의미를 식별할 근거가 부족한 호출은 ‘미확인’입니다. `raise`/`throw`는 일반 결과 반환과 분리됩니다. `semantic_status`의 문법 근거/해석 후보/미확인 구분은 실제 실행 성공 여부와 별개입니다.

분석 범위의 `analysis_quality`와 `diagnostics`는 파일 읽기, Python AST 파싱, JS/TS/Dart 패턴 분석, 파싱 실패, 생성된 처리 지도 내 대상 미확인 호출을 구분합니다. 미확인 수는 정확도 점수가 아닙니다. 호출별 `resolution_basis`와 `resolution_reason`을 보존하며, Python에서도 명시적으로 확인하지 못한 import·재바인딩·동적 속성은 미확인으로 남깁니다.

대상 저장소 코드를 실행하거나 패키지를 설치하지 않습니다. Supabase SDK와 PostgreSQL 드라이버가 발견되어도 같은 운영 DB인지 임의로 결론내리지 않습니다.

## 선택적 AI

키 없이 분석과 시각화가 작동합니다. 서버 환경변수 `OPENAI_API_KEY`, `OPENAI_MODEL`을 설정하고 사용자가 `AI 설명 추가`를 선택할 때만 기존 노드의 설명을 요청합니다. 일부 코드 근거가 외부로 전송되므로 하드코딩된 비밀을 먼저 제거해야 합니다. `.env`는 자동으로 읽지 않습니다. 이번 검증에서는 유료 AI를 호출하지 않았습니다.

## 설계와 기록

[프로젝트](docs/PROJECT.md) · [아키텍처](docs/ARCHITECTURE.md) · [계약](docs/CONTRACTS.md) · [Skills/오케스트레이션](docs/ORCHESTRATION.md) · [실행 검증](docs/EXECUTION_VALIDATION.md) · [수정 기록](docs/CORRECTIONS.md) · [개선 순서](docs/IMPROVEMENTS.md) · [Codex 인계](docs/CODEX_HANDOFF.md)

`AGENTS.md`와 `.agents/skills/`의 두 Skill은 개발 절차입니다. 제품 파이프라인은 `app/orchestrator.py`의 INTAKE → EXTRACT → BUILD → VERIFY → EXPLAIN(선택)입니다. Skill 파일 자체를 워커처럼 실행하지 않습니다.

## v0.3 실제 소스 인수 검사

```bash
python scripts/capture_reference.py --output evidence/reference/snapshot.json
python scripts/acceptance_flow.py --snapshot evidence/reference/snapshot.json
python scripts/process_browser.py --snapshot evidence/reference/snapshot.json --url http://127.0.0.1:8000
python scripts/build_review_demo.py evidence/acceptance/analysis.json demo.html
```

`process_browser.py`는 실행 중인 서버를 사용합니다. `--bridge`는 명시적인 TestClient 대체 검사이며 일반 HTTP 검증으로 부르지 않습니다. 새 데모는 실제 분석 JSON을 동일한 화면으로 재생합니다. [v0.3 계약](docs/CYCLE_04_CONTRACT.md)을 기준으로 의미 검사와 화면 검사를 분리합니다.
