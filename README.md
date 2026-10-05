# FlowLens

**프로젝트 전체 실행 경로를 먼저 보고, 특정 기능을 펼쳐 코드 근거까지 탐색하는 로컬 MVP.**

System Flow → Feature Flow → Evidence. 두 다이어그램은 같은 사실 그래프의 다른 보기입니다. 소스 코드를 실제로 실행해 얻은 runtime trace는 아닙니다.

![System Flow](evidence/system-flow.png)

## 먼저 살펴보기

`demo.html`을 브라우저로 열면 설치 없이 화면을 탐색할 수 있습니다. 두 합성 저장소를 실제 분석기로 처리한 결과가 들어 있습니다. **이 HTML만으로 새 저장소를 분석하거나 AI를 호출하지는 않습니다.** 실제 분석은 아래 서버를 실행하세요.

FlowCare는 Flutter/Hono 구조를 시험하기 위한 합성 예제이며 실제 VibeCare 저장소가 아닙니다. TaskBoard는 React/FastAPI 합성 예제입니다. 두 예제는 분석 입력일 뿐 실행할 앱이 아니므로 fixture 안에서 패키지를 설치하지 마세요.

## Windows에서 실행

먼저 Python 3.11 이상인지 확인합니다. 테스트 환경은 Python 3.13.5였습니다.

```powershell
cd .\flowlens
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

브라우저 주소창에 `http://127.0.0.1:8000`을 입력합니다. Node.js나 npm 설치는 실행에 필요하지 않습니다. PowerShell의 `Activate.ps1`을 실행하지 않아도 됩니다.

macOS / Linux:

```bash
cd flowlens
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

기본 주소는 localhost 전용입니다. 포트가 사용 중이면 기존 실행을 종료하세요. 호스트 검증도 localhost로 제한되어 있으며, 이 서버를 그대로 인터넷에 공개하면 안 됩니다.

## 사용 순서

1. 왼쪽 합성 예제 또는 상단의 공개 GitHub URL / 폴더 선택 / ZIP 선택으로 소스를 불러옵니다.
2. System Flow에서 화면·상태·서비스·백엔드·인프라의 큰 구조를 봅니다.
3. 오른쪽 기능 카드에서 로그인·측정·추천 등 인식된 API 기능을 선택합니다.
4. Feature Flow에서 관련 파일 노드나 화살표를 선택해 실제 줄 근거와 정의된 심볼을 확인합니다.
5. 상단 상위 구성요소 또는 System Flow 탭으로 돌아갑니다. JSON/SVG/Markdown으로 결과를 내보낼 수 있습니다.

`분석 과정` 화면은 실제 실행된 단계, 소스 수집 범위, 생략·실패, 미확인 관계를 보여줍니다. 그래프는 Ctrl+휠 / +/-로 확대하고 빈 공간을 드래그해 이동할 수 있습니다.

## 선택적 AI 설명

API 키가 없어도 정적 분석·두 지도·근거 탐색은 작동합니다. AI는 **이미 발견한 노드를 설명하는 역할**이며 새로운 사실·화살표를 만들지 않습니다.

유료 외부 호출을 사용할 때만 서버를 실행하는 터미널에 환경변수를 설정합니다.

```powershell
$env:OPENAI_API_KEY = "본인의 API 키"
$env:OPENAI_MODEL = "계정에서 사용 가능한 Structured Outputs 지원 모델 ID"
.\.venv\Scripts\python.exe run.py
```

그다음 화면의 `AI 설명 추가`를 선택하고 분석합니다. **선택된 코드 근거 일부가 OpenAI로 전송**됩니다. 하드코딩된 비밀 값은 먼저 제거해야 합니다. 이름 기반 제외와 일부 문자열 마스킹은 모든 비밀 탐지를 보장하지 않습니다.

`.env.example`은 변수 이름 안내이며, `.env`를 자동으로 읽는 기능은 없습니다. 키를 코드·브라우저·Git에 저장하지 마세요. 일반 공개 GitHub 요청에 필요하면 서버 환경변수 `GITHUB_TOKEN`을 사용할 수 있으나 이 버전은 여전히 공개 저장소만 허용합니다.

## 설계 먼저 보기

| 문서 | 내용 |
| --- | --- |
| [PROJECT.md](docs/PROJECT.md) | 문제 정의, 범위, 비목표, 완료 기준 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 공유 그래프와 두 가지 투영, 기술 선택 |
| [ORCHESTRATION.md](docs/ORCHESTRATION.md) | 개발용 Skills vs 제품의 런타임 파이프라인 |
| [CONTRACTS.md](docs/CONTRACTS.md) | 노드·간선·근거·기능·AI 출력 계약 |
| [VERIFICATION.md](docs/VERIFICATION.md) | 기존 설계 검증 기록 |
| [EXECUTION_VALIDATION.md](docs/EXECUTION_VALIDATION.md) | v0.2 실제 실행·ZIP·GitHub 검증 결과 |
| [IMPROVEMENTS.md](docs/IMPROVEMENTS.md) | 다음 개선 우선순위와 완료 기준 |
| [CORRECTIONS.md](docs/CORRECTIONS.md) | 이번 검증에서 발견하고 수정한 항목 |
| [CODEX_HANDOFF.md](docs/CODEX_HANDOFF.md) | 이어서 작업할 때의 프롬프트와 우선순위 |
| [SOURCES.md](docs/SOURCES.md) | 참고한 공식 문서 |

### Codex용 Skills

```text
AGENTS.md                             상시 규칙·경계·검증 명령
.agents/skills/
  flowlens-orchestrator/SKILL.md       조사 → 계약 → 테스트 → 구현 → 검증
  architecture-evidence-reviewer/
    SKILL.md                          출처·상하위 대응·과장 여부 검토
```

이 두 Skill은 개발하는 Codex가 참고할 절차입니다. 제품 서버에서 Skill 파일을 워커처럼 실행하지 않습니다. 독립 멀티에이전트를 실행했다는 의미도 아닙니다.

제품의 실행 순서는 `app/orchestrator.py`에 있습니다.

```text
INTAKE → EXTRACT → BUILD → VERIFY → EXPLAIN(선택) → 응답
                     │
                하나의 사실 그래프
                   ├─ System Flow
                   └─ Feature Flow
```

## 구현 범위와 한계

- Python은 표준 AST, JS/TS/Dart는 주석·문자열을 분리한 제한적 패턴 추출입니다. import·API·HTTP 요청·정의된 심볼이 주요 입력입니다.
- **기능별 지도는 현재 파일 단위 의존 관계**입니다. 함수 간 완전한 호출 그래프, 비동기 실행 순서, 런타임 호출 성공을 검증하지 않습니다.
- 실선은 정적 소스 관계입니다. HTTP method/path 일치와 설명용 사용자 진입은 후보 점선입니다. 서버 URL·route prefix·동적 DI·alias·조건 분기를 완전 해석하지 않습니다.
- GitHub 기본 브랜치의 commit/tree/blob을 고정해 읽습니다. 직접 clone, 코드 실행, 외부 패키지 설치, 저장소 수정은 하지 않습니다.
- GitHub 최대 48파일, 로컬/ZIP 분석 최대 160파일, 파일당 64 KiB, 총 분석 2 MiB. ZIP 자체는 최대 12 MiB이며 메모리에서 안전하게 읽습니다. 대상이 크면 일부만 분석하고 생략 수를 표시합니다. README·테스트·빌드 결과는 분석 소스에서 제외됩니다.
- Supabase와 PostgreSQL이 같은 배포인지 SDK import만으로 확정하지 않습니다. 미확인 인프라를 임의 생성하지 않습니다.
- 오류·rate limit·시간 초과·AI 미설정은 안내합니다. AI가 잘못된 ID/근거를 내면 설명을 버리고 정적 지도를 유지합니다.
- 공개 저장소·로컬 개발용입니다. 인증, 영구 저장, 비공개 저장소, 서버 배포, 의미 기반 자유 질의는 범위 밖입니다.

## 검증

개발 의존성 설치:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_skills.py
```

선택적 JavaScript 구문 검사: `node --check static/app.js`.

브라우저 검사:

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
# 다른 터미널에서 run.py를 실행한 상태
.\.venv\Scripts\python.exe scripts/browser_smoke.py
```

`--bridge`는 실제 FastAPI TestClient와 브라우저 UI를 메모리에서 연결하는 테스트 모드입니다. 정상 HTTP 접근과 다르며, 이 빌드 환경에서는 브라우저 URL 접근 정책 때문에 bridge 모드로 12개 항목을 확인했습니다. 정책을 변경하지 않았습니다.

**현재 기록(v0.2.0):** Python 테스트 64개, JS 구문 검사, 실제 localhost ZIP 분석, 브라우저 bridge 12개 항목 통과. 연결된 GitHub에서 실제 VibeCare 저장소 구조를 확인했지만 이 실행 컨테이너의 외부 DNS 제한 때문에 앱 프로세스의 live GitHub HTTP 요청은 재현하지 못했습니다. `scripts/live_github_check.py`로 일반 네트워크 환경에서 재검증할 수 있습니다. 자세한 실행 증거는 `evidence/`에 있습니다.

## 프로젝트 구조

```text
app/          API · 입력 수집 · 추출기 · 그래프 · 검증 · AI 설명
static/       무빌드 HTML/CSS/JavaScript · SVG 탐색 화면
fixtures/     실제 제품이 아닌 두 합성 분석 예제
tests/        그래프·안전성·API·외부 요청 mock·회귀 검증
scripts/      Skill 검사 · 브라우저 QA · 오프라인 데모 생성
docs/         구현 전 설계와 인계 문서
evidence/     실제 테스트 출력·화면 캡처
.agents/      개발용 Skills
```

이 패키지는 로컬 프로토타입입니다. 원래 VibeCare 저장소와 운영 데이터는 수정하지 않았습니다.
