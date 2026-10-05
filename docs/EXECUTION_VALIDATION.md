# FlowLens v0.2.0 실행 검증 기록

검증 일자: 2026-10-06

## 이번 변경에서 검증한 범위

이번 사이클의 목표는 **실제 GitHub 저장소 URL 또는 ZIP 파일을 입력으로 받아 System Flow → Feature Flow → Evidence 파이프라인까지 연결되는지** 확인하는 것이었다.

### 1. 자동 테스트

```text
pytest -q
64 passed
```

검증 범위:

- 기존 System/Feature/Evidence 회귀 테스트
- GitHub URL 형식 및 GitHub API 응답 Mock
- GitHub commit/tree/blob 고정 읽기
- rate limit / 404 / 잘린 tree / symlink 처리
- ZIP 공통 루트 폴더 제거
- ZIP path traversal 차단
- ZIP 바이너리 소스 거부
- ZIP API end-to-end 분석
- 근거 ID·줄 번호·상하위 그래프 일관성 gate

### 2. 실제 ZIP 파일 서버 분석

실제 `FlowLens_MVP_v0.1.zip`(약 745 KiB)을 실행 중인 FastAPI 서버의 `/api/analyze-zip`으로 전송했다.

결과:

```text
source: zip
archive files discovered: 85
eligible files: 15
analyzed files: 15
failed: 0
partial: false
recognized API features: 4
pipeline: INTAKE → EXTRACT → BUILD → VERIFY → EXPLAIN(skipped)
```

ZIP은 디스크에 압축 해제하지 않고 메모리에서 읽는다. 대상 코드 실행이나 패키지 설치도 하지 않는다.


### 2-1. v0.2.0 자체 ZIP 재분석

최종 패키지 `FlowLens_MVP_v0.2.0.zip`도 같은 HTTP 경로로 다시 분석했다.

```text
archive files discovered: 95
eligible files: 16
analyzed files: 16
failed: 0
partial: false
recognized API features: 5
  - Health
  - Analyze
  - Analyze Zip
  - Demo
  - Root
```

즉 새로 추가한 `/api/analyze-zip` 자체가 다음 ZIP 분석 결과에서도 인식되었다. 결과 원본은 `evidence/09-v020-self-zip-analysis.json`에 보관한다.

### 3. HTTP 서버 실행

```text
GET /api/health
200 OK
version: 0.2.0
mode: local-first
```

localhost 서버와 ZIP POST 경로가 실제 HTTP 요청에서 동작함을 확인했다.

### 4. 브라우저 UI 검증

이 실행 환경에서는 Chromium의 localhost 직접 navigation이 관리자 정책으로 차단되었다. 따라서 기존 Playwright bridge 모드로 실제 FastAPI `TestClient`와 UI를 연결해 다음 12개 항목을 확인했다.

- System overview 표시
- Feature Flow 진입
- 코드 근거 표시
- 연결 근거 표시
- 확대/맞춤
- JSON/SVG/Markdown export payload
- 분석 과정 표시
- 서로 다른 기술 스택 전환
- 도움말 dialog
- 로컬 폴더 선택 분석
- 모바일 430px overflow 확인
- JavaScript page error 없음

ZIP 버튼/엔드포인트는 API 테스트와 실제 HTTP POST로 별도 확인했다.

## 실제 GitHub 검증

연결된 GitHub 계정에서 `Dowon-Kang/vibecare-pilot`의 실제 repository tree와 다음 기술 근거를 확인했다.

- Flutter + Riverpod
- Dio client
- Hono backend
- Supabase Flutter SDK
- PostgreSQL `pg` driver
- auth / measurement / recommendation routes

따라서 FlowLens가 대상으로 삼는 대표 구조가 실제 저장소에 존재함은 확인했다.

다만 **현재 실행 컨테이너는 외부 DNS가 차단**되어 `app/intake.py`의 `httpx`가 `api.github.com`에 직접 접속하는 live end-to-end 테스트는 실행하지 못했다. 서버는 이 상황에서 오류를 fake success로 바꾸지 않고 다음 오류를 반환했다.

```text
GitHub 연결 또는 응답 해석에 실패했습니다. 로컬 폴더 분석을 사용할 수 있습니다.
```

로컬/일반 개발 환경에서 아래 명령으로 live GitHub 경로를 다시 확인할 수 있다.

```powershell
python scripts/live_github_check.py https://github.com/Dowon-Kang/vibecare-pilot
```

GitHub rate limit이 필요한 경우에만 `GITHUB_TOKEN`을 서버 환경변수로 제공한다.

## 현재 판정

| 기능 | 판정 |
| --- | --- |
| 합성 예제 분석 | PASS |
| 로컬 폴더 분석 | PASS |
| ZIP 파일 분석 | PASS |
| ZIP 안전성 gate | PASS |
| 실제 HTTP ZIP 분석 | PASS |
| GitHub API Mock E2E | PASS |
| 실제 GitHub repository 존재/구조 확인 | PASS |
| 앱 프로세스 → api.github.com live 요청 | ENVIRONMENT BLOCKED |
| AI 설명 live 호출 | NOT TESTED |

`ENVIRONMENT BLOCKED`는 구현 실패로 판정하지 않지만, 배포/사용자 PC에서 반드시 재검증해야 한다.
