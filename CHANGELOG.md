# Changelog

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
