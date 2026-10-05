# FlowLens v0.3.0 실행·수정·검증 — Cycle 04

검증 일자: 2026-10-06 KST. 대상 저장소: `Dowon-Kang/Flowlens`.
검증 후 저장된 일반 소스: `b24196aea2e7a35cb5c30cfe341db2529e069938`.
읽기 전용 CI로 전환하고 main에 반영한 커밋: `3375806a58d7dbde93aa21d2149b8a2dc5a02f61`.
이 문서는 이후 문서 전용 변경이며 위 런타임 소스는 바꾸지 않는다.

## 결론

전체 기술 구조 → 기능의 처리 단계 → 연결 가능한 함수 내부 → 실제 파일·줄 근거가 이어지도록 구현했다. 파일 의존성 그래프는 별도의 참고 보기로 남겼다. 실제 VibeCare 입력으로 조작뿐 아니라 출력 내용의 인수 기준도 검사했다.

**이것은 정적 코드 탐색 결과이지, VibeCare를 실행해 관측한 runtime trace가 아니다.** 단계명은 식별자·문장 형태에 따른 규칙 기반 해석, 화살표는 소스 읽기 순서, 함수 연결은 정적 후보다. 조건·반복·조기 반환·동적 호출은 실제 실행 경로를 바꿀 수 있다.

## 실제 실행 결과

| 검사 | 관측 결과 |
|---|---|
| 수정 후 자동 테스트 | 87 passed, 제3자 DeprecationWarning 1건 |
| Skills 형식·JavaScript 구문 | PASS |
| 실제 HTTP 서버·자체 소스 ZIP | PASS, 지원 11파일 분석 / 실패 0 |
| 일반 Chromium → HTTP 기본 화면 검사 | 13 checks PASS |
| 실제 VibeCare 소스 의미 검사 | 7개 인수 기준 PASS |
| 실제 Chromium ZIP 업로드·함수 내부 탐색 | 14 checks PASS, 17개 API/SDK 진입점 순회 |
| JavaScript 페이지 오류 | 0 |
| 실제 VibeCare GitHub URL 분석 | 지원 74개 중 74개, 생략 0, 실패 0 |
| 같은 커밋의 GitHub 다운로드 ZIP | 지원 74개 중 74개, 생략 0, 실패 0 |
| 저장 결과 HTML 재생 검사 | 7개 탐색 검사 PASS; 로컬 메모리 로드 방식 |
| 유료 AI 호출·VibeCare 코드 실행·운영 배포 | 실행하지 않음 |

실제 대상 커밋: `69307b9015f420803a132048ee98031c322d3cc1`.
186개 파일 중 문서·테스트 등 112개를 제외하고 지원 정책에 해당하는 소스 74개를 읽었다. 읽은 크기는 434,738 bytes다. `partial=false`는 이 지원 범위를 모두 읽었다는 뜻이지 모든 파일·언어·동적 동작을 완전히 해석했다는 뜻이 아니다.

GitHub/ZIP 수집 예산을 최대 160파일로 맞췄다. 파일당 64 KiB, 전체 2 MiB 제한은 유지했다. ZIP 원본은 최대 12 MiB, 내부 항목은 최대 2,500개다.

## 요구사항에 대한 관측

- 전체 보기: 사용자 포함 8개 노드. Flutter, Riverpod/Controller, Service/Dio, Hono, PostgreSQL client, Supabase 및 `api.thefitrus.com` 기본 URL 근거를 표시했다. 기본 URL은 실제 요청 성공으로 표시하지 않는다.
- 기능: 11개 그룹, API/SDK 진입점 17개, 라우트·함수·SDK 본문 지도 45개를 만들었다.
- 추천 API: 16개 세부 처리를 첫 화면에서 최대 8개 연속 묶음으로 접고, 전체 단계와 각각의 근거를 펼칠 수 있다.
- 추천 계산: `calculateRecommendation`의 실제 본문으로 들어가며, 등급 분류에서 `skeletalMuscleLevel` 내부까지 내려간다. 호출은 실행 확정이 아닌 정적 연결 후보다.
- 소스에서 안전 확인이 등급 분류보다 앞에 나타나는 순서를 유지했다. 보기 좋은 업무 흐름을 만들려고 순서를 바꾸지 않았다.
- Health: 이전 관련 파일 26개 문제를 1개 파일·1개 응답 처리로 줄였다. 같은 등록 파일의 추천 기능을 따라가지 않는다.
- Backend PIN/refresh와 Supabase SDK 로그인/회원가입/로그아웃을 별도 진입점으로 분리했다.
- 파일 참고도, 상위 기능 맥락, 함수 내부에서 돌아가기, 430px 페이지 수평 overflow 없음 등을 실제 브라우저에서 확인했다. OS 저장 대화상자나 모든 기기에서의 가독성을 보장하는 검사는 아니다.

## 실행 → 발견 → 수정 → 재검증

1. 기존 v0.2.1에 새 인수 테스트를 적용해 7개 실패를 확인한 뒤 본문 범위·처리 단계·함수 연결을 구현했다.
2. 추가 검사에서 정규식 `/destroy()/`를 함수 호출로 오인하는 실패 1건을 재현했다. 일반적인 정규식 위치를 마스킹하고 전체 87개 테스트를 다시 통과시켰다. 완전한 JavaScript 문법 지원으로 해석하지 않는다.
3. 브라우저 검사에서 같은 이름의 파일 참고도 버튼이 둘 있어 strict locator가 실패했다. 검사 선택자를 toolbar로 한정했다. 강제 클릭이나 제품 보안 정책 완화로 통과시키지 않았다.
4. 첫 원격 실행은 제품 검사·실제 GitHub/ZIP·본문 의미·브라우저 탐색까지 통과했지만, 마지막 소스 저장에서 CI 토큰의 workflow 수정 권한이 없어 실패했다.
5. 소스 저장과 workflow 설정 변경을 분리했다. CI에는 추가 workflow 권한을 부여하지 않았다. 재실행 후 소스 저장까지 성공했고, 연결된 GitHub 도구로 상시 검사를 contents:read로 전환했다. 임시 변환 스크립트는 제거했다.
6. main 반영 후 일반 회귀 검사와 기능 인수 검사를 다시 실행해 모두 completed/success를 확인했다.

## 원격 실행 근거

- 첫 실행: https://github.com/Dowon-Kang/Flowlens/actions/runs/37354054233 — 제품 검사 PASS, 최종 소스 저장 권한 오류.
- 수정 후 전체 실행: https://github.com/Dowon-Kang/Flowlens/actions/runs/37354744462 — 검사와 소스 저장 모두 SUCCESS.
- 로그·분석 JSON·실제 화면·데모·소스 묶음: https://github.com/Dowon-Kang/Flowlens/actions/runs/37354744462/artifacts/11364311725 — 7일 보관.
- 읽기 전용 검사 전환: https://github.com/Dowon-Kang/Flowlens/actions/runs/37354970679 — SUCCESS.
- main 기능 인수 검사: https://github.com/Dowon-Kang/Flowlens/actions/runs/37355132152 — acceptance SUCCESS.
- main 일반 검사: https://github.com/Dowon-Kang/Flowlens/actions/runs/37355132169 — contracts-and-browser 및 live-github-and-zip 모두 SUCCESS.

로컬 환경의 DNS와 일반 Chromium localhost navigation은 제한되어 있었다. 로컬 bridge/TestClient 검사를 일반 HTTP 검사로 대신 보고하지 않았다. 위 원격 Actions에서 일반 Chromium → 실제 HTTP 서버 → 실제 ZIP/분석 파이프라인을 별도로 수행했다. 저장 결과 HTML은 같은 제품 렌더러로 JSON을 재생하며 새 저장소나 AI를 호출하지 않는다.

## 재현

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/verify.py --browser --live https://github.com/Dowon-Kang/vibecare-pilot
python scripts/capture_reference.py --output evidence/reference/snapshot.json
python scripts/acceptance_flow.py --snapshot evidence/reference/snapshot.json
```

실행 중인 `python run.py` 서버를 대상으로 심층 UI 검사를 추가할 수 있다.

```bash
python scripts/process_browser.py --snapshot evidence/reference/snapshot.json
python scripts/build_review_demo.py evidence/acceptance/analysis.json demo.html
```

## 남은 한계

분기·예외·비동기의 완전한 제어 흐름, DI·재수출·동적 메서드·router prefix·문자열 보간 및 비표준 프레임워크는 추가 분석이 필요하다. 단계명이 문맥을 잘못 분류할 수도 있으므로 원본 근거를 함께 제시한다. 이번 검증 통과를 모든 저장소의 무오류 보장으로 확대하지 않는다.

상시 CI는 정해진 검사만 수행하며 코드를 자동 수정하지 않는다. 후속 개선도 실패 재현 → 최소 수정 → 실제 검사 → 기록 순서로 진행한다.
