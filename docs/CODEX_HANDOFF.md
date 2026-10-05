# Codex 인계

AGENTS.md, docs/PROJECT.md, docs/ARCHITECTURE.md, docs/CONTRACTS.md, docs/EXECUTION_VALIDATION.md를 먼저 읽고 `.agents/skills/`의 두 절차를 적용한다.

```text
FlowLens의 System Flow → Feature Flow → Evidence 구조를 유지하면서 개선해줘.
최근 Actions 로그와 EXECUTION_VALIDATION.md를 확인하고 재현 가능한 실패 테스트부터 추가해.
최소 수정 후 python scripts/verify.py --browser를 실행해.
네트워크가 허용되면 --live https://github.com/Dowon-Kang/vibecare-pilot도 실행해.
대상 저장소 코드를 실행하거나 수정하지 말고, 유료 AI 호출도 하지 마.
HTTP 후보를 실제 호출 성공처럼 표현하지 마.
관측한 결과만 EXECUTION_VALIDATION.md, CORRECTIONS.md, IMPROVEMENTS.md에 기록해.
승인된 Flowlens 변경만 커밋하며 force-push하지 마.
```

`--bridge`는 브라우저 UI와 FastAPI TestClient를 메모리로 연결한다. 일반 HTTP 브라우저 성공과 구분한다. 네트워크·브라우저 정책 차단 시 정책을 우회하지 말고 실패를 남긴다.
