# FlowLens v0.4.0 최종 검증·커밋·푸시 기록

## 최종 상태

`Dowon-Kang/Flowlens` PR #1을 검증 후 main에 병합했다. 런타임/테스트 소스 기준 커밋은 `41c819389f4a3b46454f2f499f97c6f2bdff099a`, main 병합 커밋은 `1d2099240aafe5a020663e92cfcb1d1b0e8e65a9`다. 이 문서와 README 갱신은 이후 문서 전용 변경이다.

- PR: https://github.com/Dowon-Kang/Flowlens/pull/1
- 구현 커밋: `8c1e11a635e9015111beb1561a8e973ade31c158`
- 원격 브라우저 실패 수정: `41c819389f4a3b46454f2f499f97c6f2bdff099a`
- main 병합: `1d2099240aafe5a020663e92cfcb1d1b0e8e65a9`

## 이번 실행 → 실패 → 수정 → 재검증

초기 로컬 구현 검사는 199개 통과였다. PR의 실제 Chromium 검사에서는 SVG에 HTML 전용 `inner_text()`를 사용한 검사 코드가 실패했다. `Node is not an HTMLElement` 오류를 아티팩트에서 확인하고, 실패를 재현하는 테스트를 추가한 뒤 SVG의 `text_content()`로 수정했다. 참/거짓 guard, 예외 근거, 미지원 fallback의 기존 assertion은 유지했다.

수정 후 **로컬 200개 테스트 통과**, JavaScript 구문/두 Skills 통과, 원격 PR CI에서도 **200개 테스트와 실제 HTTP 브라우저 15개 검사 통과**를 확인했다. 원격에서는 제3자 Starlette/anyio DeprecationWarning 1건이 있었다. 브라우저 JavaScript 페이지 오류는 0건이다.

- 첫 PR 검사: https://github.com/Dowon-Kang/Flowlens/actions/runs/37971063451 — unit PASS, browser FAIL.
- 수정 후 PR 검사: https://github.com/Dowon-Kang/Flowlens/actions/runs/37971477802 — contracts-and-browser SUCCESS. PR 정책에 의해 live-github-and-zip은 SKIPPED이며 이 run에서 통과했다고 부르지 않는다.
- main 일반 검사: https://github.com/Dowon-Kang/Flowlens/actions/runs/37971698150 — contracts-and-browser와 live-github-and-zip 모두 completed/success.
- main 기능 검사: https://github.com/Dowon-Kang/Flowlens/actions/runs/37971698163 — acceptance completed/success. 실제 공개 소스 수집, 기존 의미 검사, 실제 브라우저 업로드/함수 탐색 단계가 성공했다.

원격 PR report 시각은 `2026-10-09T18:11:37.063920+00:00`다. 원격 Python은 3.13.16이다. 원격 검사·본 문서의 결과는 이번 실행이며 과거 Cycle04/05/06 PASS를 재사용하지 않았다.

## 로컬과 원격 검사를 구분

로컬 `python scripts/verify.py --browser`는 Playwright 브라우저 실행 파일이 없어 전체 exit 1이다. 로컬 설치·시스템 Chromium 재시도·bridge·메모리 로드·보안 우회는 하지 않았다. 로컬 실패 기록은 그대로 보존했다.

별도로, 승인된 커밋/푸시가 기존 GitHub Actions를 실행했고 해당 환경의 일반 Chromium → 실제 HTTP 서버 검사를 통과했다. 워크플로와 권한을 바꾸거나 로컬 환경 정책을 우회한 것이 아니다. 브라우저 검사는 실제 ZIP 선택 → 업로드 → 활동 그래프 → guard/예외 근거 및 미지원 fallback을 포함한다. 저장 대화상자나 모든 화면 크기의 가독성까지 보장하지 않는다.

실제 localhost HTTP 폴더/ZIP 일관성 6개 기준도 통과했다. 161번째 진입점이 선택되며 160파일·64KiB·2MiB·ZIP12MiB·비밀 파일 제외 정책을 유지한다.

## 적용된 UML 범위

기존 System/Process/Code 구조에 선택적인 `활동 흐름 (UML)`을 추가했다. if/elif/else guard와 합류, 정상 반환·명시적 예외 종료를 구분한다. 의존/참조·호출·제어 흐름은 별개이며 같은 소스 근거를 재사용한다. 함수 탐색은 정적 연결 후보이고 실제 실행 trace가 아니다.

Python은 AST의 지원 문법, JS/TS/Dart는 좁은 세미콜론/균형 괄호 부분 문법이다. 미지원 본문은 활동 그래프를 만들지 않고 원본 보기로 안내한다. 시퀀스·클래스·배포 다이어그램이나 UML 전체/XMI 준수를 구현한 것이 아니다.

고정된 저장 VibeCare 소스 `69307b9015f420803a132048ee98031c322d3cc1`의 새 로컬 분석에서는 45개 처리 지도 중 **22개 활동 부분 모델, 23개 미지원**이었다. 기존 의미 검사 7개는 통과했다. `calculateRecommendation`과 추천 authorize의 복잡한 콜백/예외 처리는 아직 UML 활동 미지원이며 기존 보기로 남는다. 이 숫자는 고정 source에 대한 결과이며 새 live HEAD 전체의 보장으로 확대하지 않는다.

표현식 내부의 단락 평가·암묵적 예외·비동기 스케줄링·조건 실행 가능성은 모델링하지 않는다. 동적 바인딩/타입/DI 및 완전한 CFG는 후속 과제다.

## 변경과 보존

UML/검증 변경: `app/activity.py`, `models.py`, `process.py`, `graph.py`, `verifier.py`, `static/app.js`, `tests/test_uml_activity.py`, `tests/uml_view.cjs`, `tests/test_browser_svg_regression.py`, `scripts/check_uml_http.py`, `scripts/browser_smoke.py`, 버전/문서.

미반영 로컬 v0.3.1/0.3.2의 HTTP 의미 근거·스코프·입력 계획·진단 수정과 테스트도 함께 반영했다. 과거 기록은 보존했다. CSS, index.html, 의존성, Actions 설정, 저장소 권한, 배포 설정은 변경하지 않았다. 대상 코드는 파싱 데이터로만 사용했다. 유료 AI나 운영 배포는 실행하지 않았다. force push 없이 새 브랜치/PR/병합을 사용했다.

## 재현

```bash
python -m pytest -q
node --check static/app.js
python scripts/check_skills.py
python scripts/check_uml_http.py
python scripts/verify.py --browser
```

서버 실행 후 기능 선택 → `활동 흐름 (UML)`에서 확인한다. 원격에 올린 소스와 로컬 검증본의 Git blob/tree 해시를 대조했다. 실행 로그, 최초 실패, 성공 CI, 폴더/ZIP 결과는 별도 검증 ZIP으로 제공한다.
