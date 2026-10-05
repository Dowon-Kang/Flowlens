# 최종 근거 검토

검토 절차: `.agents/skills/architecture-evidence-reviewer/SKILL.md`.
개발과 같은 실행 주체가 절차에 따라 별도 검토했으며 독립 subagent 검토가 아니다.

**판정: CONDITIONAL PASS — 로컬 MVP.**

| 확인 기준 | 판정 | 증거/제한 |
| --- | --- | --- |
| 두 보기가 한 그래프를 공유 | PASS | graph subset 및 부모 membership 테스트, UI 상위 소속 |
| 소스 근거에 대응하는 줄·snippet | PASS | verifier 정상/변조 회귀 테스트 |
| 정적 import를 runtime call로 과장하지 않음 | PASS | UI 범례·후보 표시·help·문서에 제한 명시 |
| HTTP 연결 후보 분리 | PASS | confidence 승격 변조가 거부됨 |
| Supabase/PostgreSQL 중복 단정 방지 | PASS | 예제에 없는 PostgreSQL을 만들지 않는 테스트 |
| 입력 코드/명령 실행 금지 | PASS | 수집·추출·검증 경로에 subprocess/exec/eval/패키지 실행 없음 |
| AI의 임의 노드/근거 생성 차단 | PASS | mock Responses / 가짜 ID 회귀 테스트; 의미적 진실성은 보장하지 않음 |
| 언어/동적 호출의 완전성 | 제한 | Python AST + JS/TS/Dart lexical, 누락 가능. 함수 호출 그래프 미구현 |
| 정상 HTTP/실제 외부 서비스 | 미검증 | localhost HTTP client 확인, 브라우저는 bridge; GitHub/AI는 mock |

별도 명령 출력은 `evidence/04-evidence-review-tests.txt`. 전체 테스트 결과는 `03-final-tests.txt`.

비밀 파일 제외/일부 문자열 마스킹은 보조 방어이며, 정상 소스에 하드코딩된 모든 민감 정보를 찾는 감사 도구는 아니다. AI 호출과 JSON/Markdown 공유 전에 사용자가 소스를 확인해야 한다.
