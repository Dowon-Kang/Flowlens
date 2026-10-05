# FlowLens

**전체 시스템 → 기능 처리 단계 → 함수 내부 → 실제 코드 근거**를 탐색하는 로컬 분석기입니다. 두 다이어그램은 하나의 정적 그래프를 서로 다른 깊이로 보여줍니다. 대상 코드를 실행해 관측한 runtime trace는 아닙니다.

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

## 구현 범위

Python AST와 JS/TS/Dart의 제한된 패턴을 분석합니다. 본문 범위를 분석한 처리 지도와 파일 단위 참고도를 제공합니다. 완전한 제어 흐름·함수 호출 그래프는 아닙니다. 단계명은 식별자·문장 형태에 근거한 규칙 기반 해석이며 AI의 검증된 업무 지식이 아닙니다. 단계 사이 화살표는 **소스 읽기 순서**이며, 분기·반복·조기 반환 때문에 실제 실행 순서와 다를 수 있습니다. 명시적 import/로컬 함수로 연결한 호출도 `정적 후보`입니다. 실선은 정적 소스 관계, HTTP 점선은 method/path 일치 후보입니다. 동적 URL·라우트 prefix·DI·실행 성공을 완전히 해석하지 않습니다.

GitHub는 커밋을 고정하며 GitHub/ZIP/폴더 모두 최대 160파일, 파일당 64 KiB, 총 2 MiB입니다. ZIP은 12 MiB, 내부 항목은 2,500개까지 받으며 압축 해제 전에 읽기 예산을 적용합니다. 문서·테스트·빌드 결과·비밀 파일은 제외합니다. 제한·생략·실패는 결과에 표시합니다.

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
