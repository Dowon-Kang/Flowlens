# FlowLens v0.2.1 실행 검증 — Cycle 03

검증: 2026-10-06 KST. 대상: `Dowon-Kang/Flowlens`.
검증된 소스 commit: `5923cc4d96b6ee9a020a0ec6d0a43be44a9dab43`.

## 결과

| 검사 | 실제 관측 |
|---|---|
| 기존 자동 테스트 | 64 passed |
| 수정 전 새 회귀 검사 | 8 failed, 2 passed |
| 수정 후 자동 테스트 | 74 passed; CI에서 제3자 deprecation warning 1건 |
| Skill 형식 / JavaScript 구문 | PASS |
| localhost HTTP 서버 및 자체 소스 ZIP | PASS, 분석 9파일 / 실패 0 / 기능 5개 |
| 일반 Chromium → HTTP 서버 UI | 13 checks PASS, JavaScript page errors 0 |
| 실제 VibeCare GitHub URL | PASS, 분석 대상 74개 중 48개 읽음 / 26개 제한 생략 / 실패 0 |
| 같은 commit의 GitHub 다운로드 ZIP | PASS, 분석 대상 74개 모두 읽음 / 실패 0 |
| 유료 AI 호출 / VibeCare 코드 실행 | NOT RUN |

브라우저 검사는 전체 지도, 기능별 지도, 코드·연결 근거, 확대, 내보내기 payload, 분석 과정, 예제 전환, 폴더·ZIP 선택, 430px 화면을 검사했다. OS 저장 대화상자는 검사하지 않았다. 실제 GitHub/ZIP 분석은 별도의 실제 HTTP API 검사로 수행했다.

## 실패 → 수정 → 재검증

[첫 원격 실행 37344388644](https://github.com/Dowon-Kang/Flowlens/actions/runs/37344388644): GitHub/ZIP PASS, browser FAIL. Playwright의 문자열 평가 대기가 CSP의 unsafe-eval 금지에 걸렸다. 앱 보안 정책을 완화하지 않고 locator 기반 대기로 변경했다.

[재검증 37344830770](https://github.com/Dowon-Kang/Flowlens/actions/runs/37344830770): 전체 PASS. `report.json` 시각은 2026-10-05T16:58:42Z, Python 3.13.15, browser transport HTTP. 성공 후 검증된 일반 소스가 위 commit으로 저장되었다. [로그·스크린샷·분석 JSON](https://github.com/Dowon-Kang/Flowlens/actions/runs/37344830770/artifacts/11359798127)은 7일 보관 아티팩트다.

로컬 작업 환경의 DNS 및 일반 Chromium navigation은 정책상 차단되어 별도 기록했다. 로컬 bridge 13개 성공을 일반 HTTP 성공으로 대체하지 않았고, 일반 HTTP 검사는 원격 Actions에서 실제 수행했다.

## 실제 분석 결과

VibeCare commit: `69307b9015f420803a132048ee98031c322d3cc1`.
저장소 파일 186개 중 지원·선택 정책에 해당하는 소스는 74개. 문서·테스트 등 112개는 제외했다. ZIP의 partial=false는 이 74개를 모두 읽었다는 의미이지, 186개 전체를 의미하지 않는다.

두 입력에서 사용자 + Flutter App + Riverpod/Controller + Service/Dio + Hono Backend + PostgreSQL client + Supabase, 총 7개 overview 노드를 만들었다. 기능 그룹은 10개이며 로그인/인증, Fitrus, 추천 등이 포함된다. HTTP method/path 연결 후보는 6개다.

GitHub 입력은 48파일 제한으로 import 11건이 미해결이다. ZIP은 더 많은 소스를 읽어 일부 연결이 추가된다. 두 결과를 완전히 동일한 그래프나 실제 runtime 실행 경로라고 부르지 않는다. Supabase와 PostgreSQL이 같은 운영 DB인지는 확정하지 않는다.

## 재현

```bash
python scripts/verify.py --browser
python scripts/verify.py --browser --live https://github.com/Dowon-Kang/vibecare-pilot
```

검사기는 서버를 직접 시작·종료하고 `evidence/latest/EXECUTION_VALIDATION.md`, `report.json`, 로그를 생성한다. 네트워크 실패를 가짜 데모 성공으로 바꾸지 않는다. 상시 Actions는 읽기 권한으로 검사하며 코드를 자동 수정하지 않는다.
