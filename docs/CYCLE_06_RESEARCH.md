# Cycle 06 — 유사 도구의 공개 방식과 FlowLens 적용 경계

확인일: **2026-10-06 KST**. 공식 저장소 README·공식 문서를 직접 확인했다. 아래 내용은 해당 시점의 문서 관측이며, 각 제품을 실행해 성능이나 정확도를 비교한 벤치마크가 아니다. 제3자 소스 코드를 복사하거나 새 라이브러리를 설치하지 않았다.

## 선택한 방식

| 공식 출처 | 확인한 방식 | FlowLens에서 한 일 | 하지 않은 일 |
|---|---|---|---|
| CodeBoarding 엔진 README | 정적 분석으로 관계를 추출하고 모델은 구성요소 이름·설명에 사용. source reference가 포함된 analysis.json과 계층형 지도 | 기존 단일 근거 그래프·선택적 설명 경계를 유지. 호출 대상에 연결 근거와 미확인 사유를 붙이고 검사기가 데이터 계약을 재검사 | CodeBoarding 엔진·LSP 설치, 그 제품과 같은 분석 정확도 주장, AI가 관계를 추가하도록 변경 |
| Sourcegraph Code Navigation | 검색 기반 탐색과 인덱스 기반 precise navigation을 구분 | Python은 이름만 맞추는 탐색 대신 명시적 import·별칭·가까운 스코프를 AST로 확인. 재바인딩·그림자 변수·동적 대상은 unresolved로 보존 | SCIP 생성, compiler-grade precise navigation, 모든 언어의 타입 해석 |
| AWS Labs codeknit README | unresolved/ambiguous 관계와 진단을 보존하고 부분 결과·제외 사유를 명시 | 읽기 coverage와 AST/패턴/파싱 실패를 분리. 추출된 처리 지도 내 대상 미확인 호출·의미 미확인 단계 수를 JSON 및 기존 범위 패널에 추가. GitHub도 공통 선별 정책 사용 | codeknit 실행·소스 이식, 모든 언어 지원·전체 호출 그래프·무오류 보장 |

## 검토했지만 이번에는 도입하지 않은 방식

Aider의 repository map은 제한된 토큰 예산에서 중요한 그래프 부분을 선택한다. FlowLens의 파일명 우선순위는 그래프 순위 알고리즘과 다르다. 이번에는 입력 방식별 선택을 동일하게 만드는 데 집중했고, PageRank·동적 관심 영역 순위·의존성 기반 파일 확장 기능은 구현하지 않았다.

LSP/Tree-sitter 같은 별도 분석 엔진 도입은 JS/TS/Dart의 다음 개선 후보지만, 설치·언어별 런타임·프로젝트 설정 해석·지원 범위 검증이 필요하다. 기존 구조를 보존하고 의존성을 추가하지 않는 이번 수정에 끼워 넣지 않았다.

## 직접 작성한 작은 구성요소

`app/python_symbols.py`는 Python 표준 AST를 읽기만 한다. 명시적으로 import한 대상과 유일한 로컬 함수 정의에 한해 정적 후보를 연결한다. 조건부 정의, 여러 재바인딩, 인자, 전역/비지역 선언, 재수출, 확인하지 못한 하위 모듈 접근은 미확인이다. 일부 안전한 연결도 보수적으로 포기할 수 있다.

`app/quality.py`는 기존 Snapshot과 생성된 처리 지도의 통계를 계산한다. `runtime_verified`는 항상 false다. Python AST 파싱 성공은 실행 가능성·컴파일 성공·업무 의미 정확도의 증명이 아니다. unresolved에는 지원하지 않는 외부 SDK와 내장 함수도 들어간다. 따라서 이 수를 전체 저장소의 오류율이나 정확도 점수로 바꾸지 않는다.

## 원문

- CodeBoarding, README의 How it works / What CodeBoarding generates: https://github.com/CodeBoarding/CodeBoarding
- Sourcegraph, Code Navigation: https://sourcegraph.com/docs/code-navigation
- Sourcegraph, Precise Code Navigation: https://sourcegraph.com/docs/code-navigation/precise-code-navigation
- AWS Labs codeknit, README의 extraction/diagnostics/limits: https://github.com/awslabs/codeknit
- Aider, Repository map: https://aider.chat/docs/repomap.html
- Python 3.13, Execution model: https://docs.python.org/3.13/reference/executionmodel.html
- Python 3.13, Expressions — comprehensions: https://docs.python.org/3.13/reference/expressions.html#displays-for-lists-sets-and-dictionaries
- Python 3.13, ast: https://docs.python.org/3.13/library/ast.html

공개 문서에서 참고한 원칙과 실제 구현·검사 결과는 별개다. 이번 실제 결과는 `CYCLE_06_EXECUTION.md`와 첨부 로그를 기준으로 한다.
