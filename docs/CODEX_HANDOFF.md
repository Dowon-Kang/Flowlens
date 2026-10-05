> **v0.3 갱신:** 아래 초기 설계 중 파일 중심 Feature Flow는 `docs/CYCLE_04_CONTRACT.md`로 대체합니다. 현재 계약은 schema 1.1: System Flow → API/SDK 본문 처리 단계 → 함수 내부/근거. 파일 그래프는 보조 보기입니다. 제품 파이프라인의 BUILD에서 `process.py`가 같은 근거 그래프에 본문 범위를 투영합니다. 단계 이름은 규칙 기반 해석, 선은 소스 읽기 순서, 호출 대상은 정적 후보입니다. 실제 실행/성공을 증명하지 않습니다. GitHub 수집 예산은 160파일(총 2 MiB)입니다.

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
