# 검증 기록 — 2026-10-05

## 판정
**로컬 분석·탐색 MVP 검증 완료. 실서비스 통합 완료라는 뜻은 아니다.**

| 영역 | 실행한 검증 | 결과 / 경계 |
| --- | --- | --- |
| Python | `python -m pytest -q` | 59개 통과 |
| JavaScript | `node --check static/app.js` | 구문 오류 없음 |
| Skills | `python scripts/check_skills.py` | 2개 name/description/경로 및 분리 검사 통과 |
| API | FastAPI TestClient | 데모·로컬 파일·입력 오류·Host/Origin 제한 확인 |
| GitHub | HTTPX MockTransport | commit 고정, 비공개 거부, 잘림, symlink, 오류 응답 확인. 실제 네트워크 아님 |
| AI | HTTPX MockTransport + 출력 검증 | 요청 스키마, 가짜 노드/근거 거부, 키 마스킹 확인. 실제 LLM 출력 아님 |
| 브라우저 | Chromium + Playwright + in-process FastAPI bridge | 12개 사용자 흐름 확인, JavaScript page error 0 |
| 서버 | 실제 uvicorn + curl localhost | health·root·정적 자원·분석 JSON 확인 |
| 오프라인 HTML | 최종 HTML을 메모리에서 로드 | 초기 지도·주의 문구·입력 숨김·기능 탐색·다른 예제 5개 확인 |

## 브라우저에서 확인한 사용자 흐름
System Flow → 측정 Feature Flow → 상위 소속 → 소스 근거 → 전체 복귀 → 화살표 근거 → 확대/맞춤 → JSON/SVG/Markdown 생성 → 파이프라인 → 다른 기술 스택 → 도움말 → 실제 폴더 입력 → 모바일 폭.

직접 브라우저의 localhost URL 탐색은 `ERR_BLOCKED_BY_ADMINISTRATOR`로 차단되어 HTML/JS와 실제 FastAPI TestClient를 연결하는 대체 경로로 검증했다. 브라우저 정책은 변경하지 않았다. 따라서 정상 브라우저→HTTP 서버의 종단 간 테스트와 동일하다고 주장하지 않는다. OS 저장 대화상자 대신 실제 생성된 Blob 내용을 검사했다. 단일 HTML도 file:// 탐색은 확인하지 못하고 동일 파일 내용을 메모리에서 로드했다.

## 대표 수용 기준과 근거
- AC-01 / AC-02: Flutter/Hono 예제 7개 전체 노드, 3개 기능. UI와 `test_graph.py`.
- AC-03: Feature ID가 canonical graph의 부분집합이며 부모 component 유지. 변조 시 verifier가 거부.
- AC-04 / AC-05: 실제 소스 줄·snippet 일치; HTTP 후보를 confirmed로 승격하면 실패.
- AC-06 / AC-07: 생략·잘림·symlink·잘못된 URL/경로·비밀 파일 제한 테스트.
- AC-08: 존재하지 않거나 다른 노드에 속하는 AI 근거 거부.
- AC-09: export JSON에 revision, schema/analyzer 버전, 단계 기록 존재.
- AC-10: 브라우저 bridge에서 UI 상호작용 확인. 정상 HTTP 경로는 별도 확인 필요.

## 확인하지 않은 것
실제 GitHub URL의 네트워크 수집 성공률, 실계정 OpenAI 응답 품질/비용/지연, 실제 VibeCare 전체 코드에서의 정확도, 큰 저장소에서 precision/recall, 복잡한 route prefix·DI·alias·비동기 호출, Windows 직접 실행, 깨끗한 가상환경에서의 다운로드/설치, CI의 GitHub Actions 원격 실행, 인터넷 공개 서비스 보안.

컨테이너 외부 DNS/패키지 다운로드가 불가능해 설치된 패키지로 실행했다. 버전은 requirements에 고정했다. 패키지 버전 호환 메타데이터는 확인했지만 재설치 성공으로 표시하지 않는다.

## 한계의 의미
테스트 59개는 지정한 사례의 통과 수다. 모든 저장소를 100% 이해한다는 정확도 점수가 아니다. 구조 검증은 근거/ID의 일관성을 확인하며, 올바른 업무 의미나 전체 실행 경로 완전성을 증명하지 않는다. 두 합성 fixture와 독립 입력 사례를 사용했으며 실제 VibeCare 운영/의학적 유효성을 검증하지 않았다.

## 증거 파일
`03-final-tests.txt`, `browser-report.json`, `offline-demo-check.json`, `http-smoke.json`, `system-flow.png`, `feature-flow.png`, `code-evidence.png`, `mobile-view.png`.
