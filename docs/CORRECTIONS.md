# v0.2.1 수정 기록 — Cycle 03

검증 날짜: 2026-10-06. 기존 64개 테스트 후 새 회귀 검사 10개 중 8개 실패를 먼저 재현했다. 수정 후 전체 74개를 재실행했다.

| 발견한 문제 | 수정 |
|---|---|
| `Dio.get<Map<String, dynamic>>()`가 요청으로 인식되지 않음 | 제한된 제네릭 형식 및 줄바꿈 지원, HTTP 연결은 candidate 유지 |
| 여러 줄 named import에서 Hono 인식 실패 | 세미콜론으로 범위를 제한한 multiline import 지원 |
| DB 드라이버가 일반 helper보다 뒤로 밀림 | 진입점·라우트·controller/provider·저장 계층 수집 우선순위 개선 |
| ZIP 한도를 적용하기 전에 불필요한 파일까지 압축 해제 | 읽기 전에 파일 수·파일 크기·총 바이트 예산 제한 |
| 큰 파일 및 symlink가 통계에서 누락 | discovered = analyzed + skipped + omitted + failed 집계 |
| 분석에서 제외되는 README의 중복 ZIP 경로를 허용 | 모든 파일 경로를 정규화한 뒤 중복 거부 |
| 사용자 노드를 더하면 전체 화면이 9개가 됨 | 실제 구성요소 7개 + 사용자 1개로 제한 |
| ZIP 선택 UI가 bridge 검사에서 빠짐 | 실제 File 바이트를 전달해 ZIP picker까지 검사 |

추가로 ZIP 수집을 동시성 제한 안으로 이동하고 event loop 밖에서 실행한다. 버전은 `app.__version__`을 공유한다. 주석·문자열 속 가짜 요청, 기존 보안·근거·AI 출력 회귀 검사도 유지했다.

원본 ZIP은 저장소에 보존하고 일반 소스를 별도로 버전 관리한다. 초기 업로드에 사용한 쓰기 권한 workflow와 일회용 변환 스크립트는 검증 후 제거했다. 상시 CI는 contents:read로만 동작한다.

이 수정은 완전한 Dart/TS 의미 분석, 실제 함수 호출 추적, 운영 DB 관계 검증을 구현했다는 뜻이 아니다.

## 원격 브라우저 검사에서 추가 발견

첫 Actions 실행에서 실제 GitHub URL/ZIP 분석은 통과했지만 Playwright의 `wait_for_function` 문자열 평가가 앱의 `script-src 'self'` 정책에 차단되었다. 앱의 CSP를 완화하지 않고 네 군데 대기를 `expect(locator).to_have_text/to_contain_text`로 교체했다. 실패 run: 37344388644. 수정 후 run 37344830770에서 13개 일반 HTTP 브라우저 검사와 GitHub/ZIP 분석을 모두 재통과했다.
