# FlowLens v0.3.1 — 분석 신뢰도·입력 일관성 수정 기록 (Cycle 05)

검사 일자: 2026-10-06 KST. 작업 기반은 대화에 첨부된 `FlowLens_MVP_v0.3.0.zip`이다.
원본 ZIP SHA-256: `a310eaca022c6f29d4221b765c6ea3d98bee712f291549eb2c5528184a3f43b1`.
**로컬 수정본만 생성했다. 이번 작업에서는 GitHub 읽기/쓰기, 커밋, 푸시, 배포, 유료 AI 호출을 하지 않았다.**
대상 저장소 코드와 테스트의 소스 문자열은 파싱 대상 데이터로만 사용했다. 실행한 것은 FlowLens 자체와 검사 코드다.

## 1. 결론과 검사 경계

요청한 오분류와 폴더/ZIP 선택 불일치를 실패 테스트로 재현하고 수정했다. 최종 자동 테스트는 **129개 통과**했다.
단, **일반 HTTP 브라우저 검증은 완료하지 못했다**. 기본 Playwright 실행 파일이 없고, 설치되어 있던 시스템 Chromium은 `ERR_BLOCKED_BY_ADMINISTRATOR`로 localhost 진입이 차단됐다. 브라우저 정책을 변경하거나 bridge/메모리 로드/원격 CI로 대체하지 않았다.
`python scripts/verify.py --browser` 전체 판정은 실제로 **exit 1**이며 PASS로 바꾸지 않았다.

새 프로젝트, React/Next.js 전환, CSS·화면 구조 개편, 의존성 변경, 워크플로 변경은 없다.
단일 근거 그래프와 System → Process → Code 탐색 구조를 유지했다.

## 2. 먼저 읽은 파일

`README.md`, `docs/CYCLE_04_CONTRACT.md`, `AGENTS.md`, 두 프로젝트 Skill, 프로젝트/아키텍처/오케스트레이션/데이터 계약 문서, `app/process.py`, `app/intake.py`, `app/models.py`, `static/app.js`, 관련 extractor/scanner/verifier/API/오케스트레이터와 기존 process/ZIP/security/graph/CI 검사 코드를 읽었다.
과거 실행 문서는 구조와 의도를 확인하는 데만 사용했다. 아래 PASS는 이번 실행에서 새로 관측한 결과다.

## 3. 실패 재현 → 수정

| 재현한 문제 | 수정 전 관측 | 수정 내용과 이유 |
|---|---|---|
| Python 사전 `cache.get('answer')` | `network` / 외부 요청 | `unknown` / 호출 의미 미확인. `.get`이라는 이름을 HTTP 근거로 쓰지 않음 |
| `raise`, `raise ValueError(...)`, `throw` | 일반 `response` | 문법 키워드의 경계를 확인해 `exception` / 예외 발생으로 분리 |
| 미해결 `login`, `saveUser`, `calculateRecommendation` 등 | auth/write/recommend로 단정되는 표시 | 호출 대상·SDK 근거가 없으면 unknown. 연결된 로컬 함수에 대한 이름 기반 의미는 candidate로 제한 |
| 이름이 client/session인 사전과 shadowing | 일부 네트워크 요청으로 인식 | 명시적 requests/httpx import·별칭·Client/Session 생성 근거를 공유하고 재할당·인자 shadowing을 보수적으로 처리 |
| JavaScript 객체의 `.get` + 무관한 Axios import | network 및 request fact | 동일 파일의 import 존재만으로 모든 객체를 HTTP 클라이언트로 보지 않음 |
| unknown 상태의 부당한 승격 | 검사기가 통과시킴 | unknown 의미를 syntax로 승격하면 verifier에서 거부 |
| 표현식 본문 화살표 함수의 암시적 반환 | 보수적 분류 수정 중 unknown으로 남음 | 함수 이름이 아니라 `=> 표현식` 문법으로 response 분류. 내부 호출의 대상은 여전히 미확인일 수 있음 |
| 폴더의 161번째 `app/main.py` | 브라우저가 정렬 전 160개로 잘라 누락 | 전체 경로·크기 목록으로 서버의 공통 정책을 적용하고, 우선순위 정렬 뒤 제한 |
| 브라우저에서 먼저 제외한 파일 | 서버 coverage에서 사라짐 | 전체 manifest와 읽기 실패 목록을 전달하고 서버가 다시 계산. 수·사유를 coverage와 JSON에 보존 |

초기 34개 추가 검사: **31 failed / 3 passed** (`red-tests.log`).
추가 검토 때 JS 객체 오인 2건과 상태 승격 1건: **3 failed / 38 passed** (`review-red.log`).
암시적 반환 회귀: **1 failed** (`implicit-return-red.log`).
그 후 기존 87개 + 추가 42개 = **129개 통과**. 기존 테스트를 삭제하거나 기대값을 완화하지 않았다.

## 4. 의미의 확실성 계약

`ProcessStep.semantic_status`를 추가했다. 기존 결과 필드·근거 ID·상위 그래프 관계는 유지한다.

- `syntax`: return/raise/throw/암시적 반환 등 문법 근거. 실제 실행 여부나 반환 성공을 의미하지 않음.
- `candidate`: 연결 가능한 함수·등록된 HTTP 클라이언트 등의 근거가 있지만 업무 의미나 실행은 확정하지 않음.
- `unknown`: 의미 근거가 부족한 호출. UI에서 ‘호출 의미 미확인’, 호출 대상이 없으면 ‘호출 대상·의미 미확인’으로 표시.

unknown·exception이 앞 단계의 다른 의미 라벨에 흡수되지 않도록 분리했다. 첫 화면의 최대 8개 묶음과 모든 단계 펼치기는 유지한다.
HTTP request fact를 찾았다는 것은 해당 정적 패턴이 있다는 뜻이다. HTTP method/path 연결은 계속 candidate이며 실제 서버 접속·성공을 보증하지 않는다.

실제 HTTP 회귀 보호: requests/httpx 직접 호출, import 별칭, from-import 별칭, Session/Client/AsyncClient, async with, fetch/Axios 및 기존 typed Dio 검사.
네트워크가 필요한 원격 호출은 테스트에서 실행하지 않았다.

## 5. 폴더/ZIP 공통 정책

새 `POST /api/file-plan`은 파일 **경로·크기 목록만** 받는다. 소스 내용은 받지 않으며 저장하지 않는다.
브라우저와 ZIP은 `app/intake.py`의 동일한 `plan_files`를 사용한다.

```text
파일 메타데이터
  → 경로·중복 검사 및 공통 루트 처리
  → 지원/제외 정책
  → 같은 우선순위 정렬
  → 파일 수·단일 크기·총 크기 제한
  → 선택된 파일만 읽기
  → Snapshot → 기존 단일 분석 파이프라인
```

폴더 제출 시 서버는 manifest로 계획을 다시 계산한다. 실제 전송 파일과 읽기 실패 목록의 합이 선택 목록과 일치하는지, 전송된 UTF-8 바이트 수가 신고 크기와 같은지 확인한다. 없는 파일/추가 파일/잘못된 크기는 성공으로 처리하지 않는다.
UTF-8을 엄격하게 읽고 BOM을 보존한다. 잘못된 UTF-8/NUL은 invalid_text로 집계한다. 실패한 선택 파일을 다른 파일로 뒤늦게 채우지 않아, 입력 방식에 따른 예산·선택 결과 차이를 방지한다.

보존한 제한: 분석 160파일 / 파일당 64 KiB / 총 2 MiB / ZIP 12 MiB / ZIP 내부 2,500항목. 폴더 메타데이터 목록도 최대 2,500개다. 소스 본문 요청은 기존 3 MiB 제한을 유지한다.
비밀·숨김·생성·테스트·빌드 파일 제외, 암호화 ZIP 거부, 경로 탈출 차단, ZIP 심볼릭 링크 제외는 유지했다. 브라우저는 제외된 파일의 **내용을 읽거나 보내지 않지만**, 계획 수립을 위해 파일명·크기 메타데이터는 로컬 서버로 보낸다.

coverage에는 `reason_counts`와 선택적인 `browser_selection`을 추가했다. 분석 범위 화면에 사유별 수를 보여주고 JSON 내보내기에도 포함된다.
`browser_selection.reported_by = "browser"`는 로컬 디스크 검증 인증이 아니다. 발견 목록·읽기 실패는 브라우저 보고이며 서버는 공통 선택 및 전송된 내용만 재검사한다.

### 161번째 진입점 테스트의 실제 결과

테스트 입력은 160개 helper 다음에 `app/main.py`를 넣었다. 제외 정책과 확장자도 함께 검증하도록 총 168개 파일로 구성했다.

| 항목 | 폴더 / ZIP의 동일 관측 |
|---|---:|
| 발견 | 168 |
| 지원 후보 | 162 |
| 분석 | 160 |
| 지원·보안 기준 제외 | 6 |
| 160개 개수 제한으로 생략 | 2 |
| 읽기 실패 | 0 |
| 부분 분석 | true |
| 입력의 161번째 main.py | 선택됨 |

제외 사유는 secret_or_hidden 2, unsupported_type 1, excluded_directory 2, generated_or_test 1, file_count 2다.
두 결과의 revision, nodes, edges, system_nodes, system_edges, features, facts, flows, evidence를 실제 HTTP 검사에서 비교해 동일함을 확인했다. source/name/입력별 설명·브라우저 보고 필드까지 완전히 같은 JSON이라고 주장하지 않는다.

## 6. 이번 실제 검사 결과

실행 환경: Python 3.13.5 / Node 22.16.0 / pytest 9.0.2 / Playwright 1.57.0.
마지막 verify 기록 UTC: 2026-10-05T23:53:42.989464+00:00 (KST 2026-10-06).

| 실제 명령 / 검사 | 관측 결과 | 로그 |
|---|---|---|
| 원본 `python -m pytest -q` | 87 passed (이번에 직접 실행한 기준선) | baseline-pytest.log |
| 최종 `python -m pytest -q` | **129 passed in 3.28s**, exit 0 | final-pytest.log |
| `node --check static/app.js` | exit 0 | final-javascript.log (정상 시 출력 없음) |
| `python scripts/check_skills.py` | 두 Skill 검사 PASS, exit 0 | final-skills.log |
| `python scripts/verify.py --browser` | **exit 1 / 전체 FAIL**. unit·skills·JS·실제 HTTP ZIP 통과, 브라우저 시작 파일 없음 | final-verify-command.log, final-verification/report.json |
| 설치되어 있던 `/usr/bin/chromium`으로 명시적 실제 HTTP 시도 | `ERR_BLOCKED_BY_ADMINISTRATOR`, exit 1. 당시 중간 수정본의 121개 테스트 단계에서 수행. 차단 뒤 시스템 Chromium의 navigation 재시도·우회 안 함 | system-browser-command.log, http-browser-system/browser-http.log |
| `python evidence/cycle-05/http_contract_check.py` | **PASS**, 자체 서버를 실제 localhost HTTP로 호출해 폴더/ZIP 비교 | final-http-contract.log, http-contract-result.json |
| Node 폴더 change handler 단위 검사 | 최종 pytest에 포함되어 PASS. File 객체/DOM 경계가 모의 객체인 단위 검사 | tests/folder_handler.cjs, final-pytest.log |
| 저장된 VibeCare 소스의 `acceptance_flow.py` 재실행 | **7개 기준 PASS**. 과거 결과 JSON 재생이 아니라 저장된 source를 현재 코드로 새로 분석 | saved-source-acceptance.log, saved-source-acceptance/report.json |
| bridge/메모리 브라우저 | **실행 안 함** | 해당 없음 |
| 실제 GitHub live 수집 / 원격 CI / 유료 AI / 대상 코드 실행 / 배포 | **이번에 실행 안 함** | 해당 없음 |

최종 verify의 자체 소스 ZIP 분석은 12개 지원 파일, 읽기 실패 0이었다. 검사기는 서버를 종료했다.
Node 핸들러 단위 검사, TestClient API 검사, httpx의 실제 HTTP 검사는 모두 **일반 브라우저 통과와 다르다**. 브라우저 업로드·화면 가독성이 검증됐다고 표시하지 않는다.
저장된 VibeCare fixture의 기준 커밋은 `69307b9015f420803a132048ee98031c322d3cc1`이다. 이번 fresh 의미 검사 7개는 이전 PASS를 재사용한 것이 아니며, 최신 GitHub HEAD를 검증한 것도 아니다.

## 7. 변경 파일

| 파일 | 변경 이유 |
|---|---|
| app/process.py | 예외/반환/미확인 분리, 의미 상태, 부당한 단계 병합 방지 |
| app/http_clients.py (신규) | Python import·수신 객체 근거의 작은 공용 AST 분석기 |
| app/extractor.py | HTTP request fact와 처리 단계가 같은 근거 정책을 사용 |
| app/intake.py | 폴더/ZIP 공통 계획, 우선순위 선적용, 제외·실패 집계 |
| app/models.py | 파일 메타데이터·읽기 실패·브라우저 보고·semantic_status 계약 |
| app/main.py | 메타데이터 전용 file-plan API, 기존 보안/크기 검사 유지 |
| app/orchestrator.py | 파일 입력의 manifest/read_failures 전달만 추가 |
| app/verifier.py | unknown/syntax 의미 상태의 모순 검출 |
| app/__init__.py | 로컬 수정본 버전 0.3.1 |
| static/app.js | 공통 계획 사용, 선택된 내용만 읽기, 범위·미확인 표시 |
| tests/test_reliability.py (신규) | 오분류 및 HTTP 회귀 검사 |
| tests/test_selection_consistency.py (신규) | 161번째 진입점·일관성·제한·집계 검사 |
| tests/folder_handler.cjs (신규) | 실제 JS 폴더 처리 함수의 Node 단위 검사 지원 |
| README.md | 로컬 수정본 상태, 계약 및 이번 결과 안내 |
| docs/CYCLE_05_RELIABILITY.md (이 문서) | 재현·설계·실행·미검증 범위를 함께 기록 |

기존 테스트, docs/CYCLE_04_CONTRACT.md, 예전 실행 기록, styles.css, index.html, 의존성 및 GitHub Actions는 변경하지 않았다. 과거 문서의 PASS는 과거 기록으로 보존했다.

## 8. 남은 한계

1. Python에서 모든 전역 재바인딩·monkey patch·동적 팩토리·DI의 타입을 증명하지 않는다. 지원하는 정적 바인딩만 활용한다.
2. JS/TS/Dart는 완전한 AST/스코프 분석기가 아니라 제한된 패턴 분석이다. 기존 Dio 후보를 보호하지만 실제 인스턴스·origin·분기 실행을 증명하지 않는다. 미지원 호출이 unknown이 되는 것은 보수적 동작이다.
3. 연결된 함수의 업무 의미 라벨도 여전히 식별자 기반 후보일 수 있다. 본문 근거가 있다고 인증·안전·계산의 정확성이 입증되는 것은 아니다.
4. 폴더와 ZIP의 같은 일반 파일 집합에 대한 선택을 비교했다. ZIP 전용 메타데이터(암호화, symlink)나 브라우저 파일 권한 실패는 완전히 같은 입력 조건이 아니며 별도 집계된다.
5. 화면 변경은 JS 구문 및 실제 핸들러 단위 수준에서 확인했다. 일반 브라우저는 환경 정책으로 미검증이다. **‘데모처럼 문제없이 보인다’고 이번 결과만으로 결론내리지 않는다.**
6. 수집/바이트/파일 개수 상한에 도달하면 계속 부분 분석이다. GitHub 대규모 저장소와 원격 네트워크는 이번 작업 범위에서 새로 검사하지 않았다.

## 9. 승인 후 적용·재검증

제공한 source ZIP은 기존 프로젝트를 그대로 수정한 전체 로컬 소스다. 함께 제공한 unified patch는 원본 v0.3.0 ZIP에 대응한다. 원격 저장소에 다른 변경이 있으면 파일 차이를 먼저 검토해야 한다.

```bash
python -m pytest -q
node --check static/app.js
python scripts/check_skills.py
python scripts/verify.py --browser
```

브라우저 정책으로 차단된 환경에서는 반복 실행이나 bridge 우회로 PASS를 만들지 않는다. 허용된 개발 환경에서 실제 HTTP 브라우저 검사를 별도로 완료해야 한다. 커밋·푸시·배포는 이번 승인 범위에 없으므로 수행하지 않았다.
