# Changelog

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
