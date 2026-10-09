# v0.4.0 — UML-informed activity slice

- Integrate the previously local v0.3.1/0.3.2 reliability fixes.
- Preserve source-order view; add guarded, evidence-linked activity control-flow.
- Separate abrupt exits, dependencies and calls; unsupported scopes fail closed.
- Add 37 regression tests and browser acceptance steps; local browser is unavailable.
- See docs/CYCLE_07_EXECUTION.md for actual results, not past PASS records.

# Changelog

## 0.3.0
- API/SDK 본문 처리 요약과 함수 내부 탐색, 연속 단계 접기.
- Health 범위 격리; PIN/refresh와 Supabase 직접 인증 분리.
- 외부 API 기본 URL 근거(후보), GitHub/ZIP 공통 160파일 예산.
- 정확한 줄 근거/정적 후보 검증 및 실제 소스 인수 검사.
- 보안 정책을 완화하지 않는 브라우저 검사, 결과 재생 데모.

## 0.2.1 · 2026-10-06

- GitHub 소스 연결 및 재사용 가능한 실행 검증 루프.
- typed Dio/multiline import, 수집 우선순위, ZIP 사전 예산·coverage, 8노드 상한 수정.
- 74 tests + 13 real HTTP browser checks + 실제 VibeCare GitHub/같은 commit ZIP PASS.
- CSP를 유지한 locator 기반 브라우저 대기. 상세 run 기록은 docs/EXECUTION_VALIDATION.md.

## 0.2.0 · 2026-10-06

### Added
- ZIP repository analysis endpoint and UI picker.
- In-memory ZIP safety gates for traversal, encrypted entries, symlinks, file count and size.
- Shared `analyze_snapshot()` pipeline so ZIP/local/GitHub sources produce the same graph contract.
- ZIP end-to-end and security tests.
- Manual `scripts/live_github_check.py` network verification command.
- `docs/EXECUTION_VALIDATION.md` and `docs/IMPROVEMENTS.md`.

### Verified
- 64 automated tests pass.
- Real FlowLens v0.1 ZIP analyzed through the running localhost HTTP API.
- 12 browser bridge checks pass without JavaScript page errors.
- Live GitHub repository structure inspected through the connected GitHub integration.

### Known limitation
- The current execution container blocks outbound DNS, so direct application-process access to `api.github.com` could not be live-tested here.
