# FlowLens v0.3.2 로컬 수정·검증 — Cycle 06

검사일: **2026-10-06 KST**. 기준: 대화에 첨부된 `FlowLens_MVP_v0.3.1_Local.zip`.
기준 ZIP SHA-256: `43e6baee462c48f23b06fb6ccbd628edef3868be91a5e25b8a6ecd5add4464d8`.

**이번에도 원격 저장소에 커밋·푸시하지 않았다. 배포·유료 AI·분석 대상 코드 실행·원격 CI 실행을 하지 않았다.** 공개 유사 서비스의 공식 문서를 웹에서 확인했고, 그 설계 원칙을 자체 코드에 적용했다. 새 프로젝트·프레임워크·의존성·CSS 개편은 없다.

## 결론

이번 실행의 기준선 **129 passed**에서 새 검사 33개를 추가해 최종 **162 passed**를 확인했다. JS 구문·Skills·실제 HTTP 폴더/ZIP 입력 비교 및 저장된 VibeCare 소스의 의미 검사도 통과했다.

**`python scripts/verify.py --browser` 전체 결과는 exit 1이다.** Playwright가 요구하는 브라우저 실행 파일이 없어 launch 단계에서 실패했다. 브라우저 설치·정책 변경·시스템 Chromium 재시도·bridge·메모리 로드·원격 CI로 대체하지 않았다. 화면 조작/표시의 최종 브라우저 검증은 남아 있다. 과거 관리자 차단 로그를 이번 명령의 실패 이유로 대신 쓰지 않는다.

## 참고한 공개 방식

CodeBoarding의 정적 관계/설명 분리, Sourcegraph의 정확한 인덱스 탐색과 검색 기반 탐색 구분, AWS Labs codeknit의 불확실한 관계·진단 보존을 참고했다. **해당 도구의 코드를 복사하거나 엔진을 통합한 것은 아니다.** 실제 채택/보류 범위와 공식 출처는 `CYCLE_06_RESEARCH.md`에 적었다.

## 읽고 보존한 설계

README, CYCLE_04_CONTRACT, Cycle05 기록, AGENTS, 프로젝트·아키텍처·오케스트레이션·데이터 계약, 프로젝트 전용 두 Skill과 분석기/입력기/모델/화면/관련 검사를 읽었다. 구현 전에 `CYCLE_06_CONTRACT.md`를 작성했다.

단일 근거 그래프, System → Process → Code 탐색, 문법 근거/의미 후보/미확인, source-order/실제 실행 미검증을 유지했다. 저장소의 과거 PASS 기록은 과거 문서로 남겨 두고 이번 결과와 섞지 않았다.

## 실패 재현과 수정

| 문제 | 실제 실패 관측 | 최소 수정 |
|---|---|---|
| Python import 별칭·모듈 별칭이 연결되지 않음 | 명시적으로 import한 함수의 callee가 없음 | 표준 AST 기반 `PythonSymbolIndex`로 import 경로와 대상의 유일한 함수 정의 확인 |
| 이름만 같은 다른 함수를 연결 | 인자·로컬 import·for/with 바인딩·재할당을 무시하거나 전역 정의로 잘못 이동 | 가장 가까운 스코프를 먼저 보고, 그림자 변수·재바인딩·조건부 정의·global/nonlocal은 미확인 |
| 컴프리헨션 내부 스코프 | 뒤쪽 iterable의 로컬 이름과 `:=`로 바뀐 이름을 전역 함수로 연결 | 첫 iterable과 내부 스코프를 구분, NamedExpr의 포함 스코프 바인딩 보수적으로 무효화 |
| import하지 않은 하위 모듈 | `import pkg`만 있는데 `pkg.logic.save()`를 연결 | 명시적 import 경계를 넘는 하위 모듈/동적 속성은 미확인 |
| 같은 줄의 HTTP/사전 `.get` | 실제 HTTP 근거가 같은 줄의 뒤쪽 사전 호출로 전이 | Python AST의 정확한 문자 오프셋과 호출 이름을 함께 사용 |
| 파일 읽기 성공과 파싱 실패 혼동 | broken.py를 읽었지만 진단 구조 없음 | `analysis_quality`, `diagnostics`를 추가하고 EXTRACT 단계에 warning |
| `.PY` 파일 지원 불일치 | 수집되지만 Python 파서/처리 지도는 실행되지 않음 | 확장자 처리를 수집·추출·그래프·본문 스캐너에서 일치시킴 |
| 미확인 호출/통계의 부당한 승격 | callee 없이 static-candidate, 틀린 집계가 gate 통과 | 연결 상태·근거·새 진단 통계 일관성을 verifier에서 재검사 |
| GitHub 총량 제한 적용 시점 | 64 KiB 40파일을 모두 다운로드한 뒤 제한 | 폴더/ZIP과 같은 `plan_files`를 blob 읽기 전에 호출. 테스트에서 32개만 다운로드 |
| GitHub 응답 오류 집계 | 잘못된 크기/인코딩을 엄격하게 구분하지 못함 | strict base64와 고정 트리의 크기 비교, read_error/invalid_text 집계 |
| 공통 루트가 보안 경계를 지움 | `.venv/main.py`, `tests/main.py` 등의 부모가 제거되어 선택됨 | 제외 디렉터리는 wrapper로 제거하지 않음. 비밀 이름의 경로 구성요소도 제외 |
| 진단·호출 미확인 사유가 화면에 없음 | helper 검사 실패 | 기존 분석 범위 패널과 호출 목록만 보완. 출력 문자열 escape, 이전 결과 fallback |

### 테스트를 수정한 이유도 구분

첫 20개 추가 검사가 실패했다. 이 중 두 소스 fixture가 분석 대상 언어의 의미상 부적절했다. `import app.logic`가 FastAPI의 `app` 변수를 가리던 예제는 `pkg`로 수정했고, 함수 내부에서 httpx를 재할당하는 예제는 첫 호출 전 로컬 import를 넣어 실제 지역 바인딩 예제가 되게 했다. **제품 수정 전 다시 실행해 여전히 20개 실패함을 확인했다.** 두 red 로그 모두 남겼다.

새 GitHub 크기 검사가 기존 모의 응답의 잘못된 메타데이터도 발견했다. `tests/test_remote_and_gate.py`의 blob 내용은 **44 bytes**인데 트리는 42라고 적혀 있었다. 내용과 메타데이터가 같은 `BLOB_CONTENT`에서 만들어지도록 fixture만 바로잡았다. 기존 검사의 assertion은 삭제·완화하지 않았다.

추가 검토에서는 제외 루트/UI 6건, 컴프리헨션 2건, import 경계 2건의 실패를 재현하고 고쳤다. 최종 새 테스트 수는 33개이며 기존 129개와 함께 통과했다.

## 데이터 계약

호출에는 `resolution_basis`와 `resolution_reason`을 추가했다. basis는 Python local/import, lexical, unresolved다. 실제 연결은 계속 static-candidate이며, Python AST를 썼다고 compiler/SCIP 수준 정확성을 주장하지 않는다. callee가 없는데 후보로 표시하거나, 후보인데 이유가 없으면 gate에서 거부한다.

`analysis_quality`는 선택한 소스의 AST/lexical/parse failure 및 **생성된 처리 지도 내** 호출 항목·미확인 단계 수를 제공한다. `diagnostics`에는 파일별 파싱 실패와 제한된 패턴 분석 안내를 남긴다. verifier는 Snapshot/기존 그래프로 집계를 재계산한다. 이것은 입력/출력의 자체 일관성 검사이지 외부 정답으로 의미 정확도를 증명하는 검사가 아니다.

파싱이 실패해도 파일을 읽은 사실은 coverage에 보존한다. 따라서 `coverage.partial=false`와 `analysis_quality.parse_failed_files>0`가 동시에 가능하다. UI는 이 차이를 설명하며, AST 파싱 성공을 완전한 해석 성공으로 표현하지 않는다. 기존 JSON은 진단 정보가 없으면 ‘이전 형식 결과’로 표시한다.

## 입력 정책과 보안 제한

GitHub/폴더/ZIP은 같은 경로·지원·제외·우선순위·읽기 예산 정책을 공유한다. 실패 파일은 예산을 소비한 상태로 남기고 입력별로 뒤늦게 다른 파일을 채우지 않는다. GitHub는 고정 커밋의 트리·blob을 읽으며 신규 코드는 모의 HTTP로 검사했다. **실제 GitHub 서비스에 대한 새 live 요청은 이번에 수행하지 않았다.**

160개 분석 파일 / 파일당 64 KiB / 총 2 MiB / ZIP 12 MiB / 목록 2,500개 상한을 유지했다. GitHub도 공통 목록 상한을 적용하므로 2,500 blob을 넘으면 명확한 오류가 날 수 있다. 대형 저장소를 전부 분석했다고 표시하지 않는다. 공통 루트 제거가 숨김·테스트·비밀 폴더의 제외 규칙을 풀지 못하게 했으며, 비밀 경로 검사는 오히려 강화됐다.

GitHub의 크기·base64 검사는 cryptographic blob 해시 검증을 뜻하지 않는다. 브라우저 발견/실패 수는 여전히 브라우저 보고이며 서버가 로컬 디스크를 검증했다는 뜻이 아니다.

## 이번 실제 검사

환경: Python 3.13.5, Node 22.16.0, pytest 9.0.2, Playwright 1.57.0. 의존성 버전 변경 없음.
최종 verify 기록: **2026-10-06T08:26:08.081801Z**.

| 실제 명령/검사 | 결과 | 증거 파일 |
|---|---|---|
| 수정 전 `python -m pytest -q` | 129 passed | baseline-pytest.log |
| 최초 새 테스트, fixture 수정 후 | 20 failed | red-tests-corrected-fixtures.log |
| 추가 경계 검토 | 6 failed / 22 passed | review-red.log |
| 컴프리헨션 검토 | 2 failed / 1 passed | scope-review-red.log |
| import 경계 검토 | 2 failed | import-boundary-red.log |
| 최종 `python -m pytest -q` | **162 passed in 1.37s**, exit 0 | final-pytest.log |
| `node --check static/app.js` | exit 0 | final-javascript.log (정상 시 빈 출력) |
| `python scripts/check_skills.py` | 두 Skill PASS, exit 0 | final-skills.log |
| 실제 localhost HTTP 폴더/ZIP 비교 | **7개 기준 PASS**, exit 0 | http/report.json, http-check.log |
| 저장된 VibeCare 소스를 현재 코드로 새 분석 | **7개 의미 기준 PASS**, exit 0 | saved-source-acceptance/report.json |
| `python scripts/verify.py --browser` | **전체 exit 1**. unit/skills/JS/HTTP ZIP PASS, browser launch FAIL | verification/report.json, browser-http.log |
| bridge·메모리 로드·시스템 Chromium 재시도·원격 CI | **이번 실행 안 함** | 해당 없음 |
| 유료 AI·대상 코드 실행·배포·커밋/푸시 | **실행 안 함** | 해당 없음 |

verify 내부 pytest도 새로 실행해 162 passed in 1.43s였다. 두 시간은 서로 다른 실제 실행이며 성능 벤치마크가 아니다. 서버는 검사 후 종료했다. 환경 버전 출력의 첫 `pip show | head`는 출력 파이프 종료로 실패했지만 앱 검사와 무관했고, importlib.metadata로 환경 정보를 다시 수집해 environment.json에 저장했다.

### 실제 HTTP의 161번째 진입점

160개 helper 뒤에 `app/main.py`를 넣고 parse-error·manifest·제외 파일을 추가한 총 168개 입력을 사용했다. 파일 내용은 합성 fixture다.

- 발견 168 / 지원 후보 164 / 분석 160 / 규칙 제외 4 / 제한 생략 4 / 읽기 실패 0.
- 161번째 main.py 선택됨. 그래프·처리 지도·근거·revision·진단 결과가 폴더와 ZIP에서 같음.
- 160개 읽기 중 manifest 1, Python 소스 159, 그중 AST 파싱 158·실패 1.
- EXTRACT warning, runtime_verified=false. 브라우저 보고 필드는 폴더에만 있으므로 JSON 전체 동일성으로 표현하지 않음.

GitHub 모의 응답에서는 같은 161번째 진입점 및 reason_counts를 비교했다. 별도 64 KiB×40파일에서는 전송 전에 32파일/2 MiB로 제한하고 나머지 8개를 total_bytes로 남겼다.

### 저장된 실제 VibeCare 소스 재분석

이번에 다시 읽고 분석한 snapshot 기준 커밋은 `69307b9015f420803a132048ee98031c322d3cc1`이다. snapshot SHA-256은 `2e8f9b52810fd9753d86ae6270f34dd02fad66dc1bf373c4825ec13b524bcb81`이다. 최신 GitHub HEAD나 이전 결과 JSON을 재생한 검사로 부르지 않는다.

지원 74파일 = JS/TS/Dart 소스 71 + manifest 3. 11기능/45처리 지도. 그 지도에서 호출 항목 456, 정적 연결 후보 54, 대상 미확인 402, 의미 미확인 단계 60이 관측됐다. **402건을 오류 402개나 정확도 11.8%로 해석하면 안 된다.** 외부 SDK·내장 함수 등 본문 연결을 하지 않는 호출도 포함되고 전체 저장소 호출을 집계한 값도 아니다.

## 변경 파일 (18개)

| 파일 | 변경 |
|---|---|
| README.md | v0.3.2 로컬 상태·이번 결과/한계 링크 |
| app/__init__.py | 로컬 버전 0.3.2 |
| app/python_symbols.py (신규) | Python lexical binding·명시적 import 후보 해석 |
| app/process.py | 새 Python 해석기, 호출 근거/사유, 동일 줄 HTTP 위치 구분 |
| app/quality.py (신규) | 읽기와 해석 진단 계산 |
| app/models.py | 분석 진단·해석 근거 추가 계약 |
| app/verifier.py | 해석 상태·진단 집계 일관성 검사 |
| app/graph.py | 진단 연결, 확장자 일관성, fallback 근거의 lexical 표시 |
| app/extractor.py | 확장자 대소문자 일관성 |
| app/flow_scanner.py | 확장자 대소문자 일관성 |
| app/intake.py | GitHub 공통 선별·사전 총량 제한·엄격한 응답·루트 제외 보호 |
| app/orchestrator.py | parse failure를 EXTRACT warning에 반영 |
| static/app.js | 기존 범위 패널·호출 목록의 진단/사유 출력과 이전 결과 fallback |
| tests/test_cycle06.py (신규) | 새 회귀 검사 33개 |
| tests/test_remote_and_gate.py | 기존 모의 blob의 실제 바이트 크기로 fixture 수정 |
| docs/CYCLE_06_CONTRACT.md (신규) | 구현 전 인수 기준 |
| docs/CYCLE_06_RESEARCH.md (신규) | 공식 방식 조사·채택/보류 구분 |
| docs/CYCLE_06_EXECUTION.md (신규) | 이번 실제 수정/검사 기록 |

기존 CSS·index.html·의존성·Skills·워크플로·브라우저 검사 스크립트·AI 호출 코드는 바꾸지 않았다. 검사 로그와 재현용 http_check.py는 별도 증거 묶음이다.

## 남은 한계와 다음 우선순위

1. 일반 브라우저의 화면·폴더 선택·진단 표시 검증이 남았다. Node 함수 검사는 DOM/HTTP 브라우저 통과가 아니다. 이번에는 새 화면 캡처나 작동 데모를 완료했다고 하지 않는다.
2. Python은 제한된 스코프/명시적 import만 다룬다. DI·monkey patch·조건부 실행·모듈 초기화·재수출·동적 속성·모든 타입/예외/비동기 제어 흐름을 해석하지 않는다. 함수 정의를 찾은 것과 호출 성공은 다르다.
3. JS/TS/Dart는 여전히 lexical 패턴 분석이다. 실제 VibeCare의 대부분이 이 범위이므로 이 부분의 범위 제한과 오분류 회귀 검사가 다음 우선순위다. SCIP/LSP/Tree-sitter를 구현했다고 주장하지 않는다.
4. 동일 정책은 같은 일반 파일 메타데이터/내용에서 비교했다. URL별 revision/evidence URL, ZIP symlink·암호화, 브라우저 읽기 권한·로컬 실패 등 입력 고유 조건은 별도다.
5. 현재 품질 집계는 진단 수이지 정확도 지표가 아니다. 일부 유효한 연결도 미확인으로 보수적으로 남길 수 있다.

## 적용

아직 GitHub에 반영하지 않은 로컬 ZIP과 v0.3.1 기준 패치다. 원격에 다른 변경이 있으면 차이를 먼저 검토해야 한다. 커밋·푸시·배포는 별도 승인 없이 수행하지 않는다.

```bash
python -m pytest -q
node --check static/app.js
python scripts/check_skills.py
python scripts/verify.py --browser
```

브라우저 설치/실행이 허용된 사용자 개발 환경에서 마지막 검사를 완료할 수 있다. 차단 환경에서는 보안 정책을 낮추거나 bridge/원격으로 PASS를 바꾸지 않는다.
