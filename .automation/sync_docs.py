"""One-time reviewed documentation update; preserve unrelated changes."""
from pathlib import Path
import hashlib
EDITS = [
('CHANGELOG.md', 'b809cdc673de1dbb84c695fcc389c75ebd7fd8bcfd6e84dc6d9705614c853e83', '8c7849c2145f059c03df00b8f2708d8dde16897d7f38a5d40d30dd4e250b5186', [
(1,1, r'''
## 0.3.0
- API/SDK 본문 처리 요약과 함수 내부 탐색, 연속 단계 접기.
- Health 범위 격리; PIN/refresh와 Supabase 직접 인증 분리.
- 외부 API 기본 URL 근거(후보), GitHub/ZIP 공통 160파일 예산.
- 정확한 줄 근거/정적 후보 검증 및 실제 소스 인수 검사.
- 보안 정책을 완화하지 않는 브라우저 검사, 결과 재생 데모.
'''),
]),
('README.md', 'c73e75c7b996d4f131c51d86855aa6a0063d24aeeafcf67dc3f21e3c5fc99516', '2517fa4e0fa84b7c999e373a18d0f1979ae5206d4b5085000225c960a6e80bc1', [
(2,3, r'''**전체 시스템 → 기능 처리 단계 → 함수 내부 → 실제 코드 근거**를 탐색하는 로컬 분석기입니다. 두 다이어그램은 하나의 정적 그래프를 서로 다른 깊이로 보여줍니다. 대상 코드를 실행해 관측한 runtime trace는 아닙니다.
'''),
(22,23, r'''상단에서 공개 GitHub 저장소 URL, ZIP 파일 또는 로컬 폴더를 선택합니다. 먼저 기술 계층별 System Flow가 나타납니다. 기능 카드를 고르면 API/SDK 진입점별 처리 단계가 먼저 나타납니다. 최대 8개 묶음으로 보고 전체 단계를 펼칠 수 있습니다. 단계 클릭 → 실제 근거 → 연결 가능한 함수 내부로 내려갑니다. 파일 의존성은 별도의 `파일 참고도`입니다. PIN·refresh와 SDK 직접 인증은 다른 진입점으로 표시합니다. JSON / SVG / Markdown 내보내기를 지원합니다.
'''),
(48,49, r'''Python AST와 JS/TS/Dart의 제한된 패턴을 분석합니다. 본문 범위를 분석한 처리 지도와 파일 단위 참고도를 제공합니다. 완전한 제어 흐름·함수 호출 그래프는 아닙니다. 단계명은 식별자·문장 형태에 근거한 규칙 기반 해석이며 AI의 검증된 업무 지식이 아닙니다. 단계 사이 화살표는 **소스 읽기 순서**이며, 분기·반복·조기 반환 때문에 실제 실행 순서와 다를 수 있습니다. 명시적 import/로컬 함수로 연결한 호출도 `정적 후보`입니다. 실선은 정적 소스 관계, HTTP 점선은 method/path 일치 후보입니다. 동적 URL·라우트 prefix·DI·실행 성공을 완전히 해석하지 않습니다.
'''),
(50,51, r'''GitHub는 커밋을 고정하며 GitHub/ZIP/폴더 모두 최대 160파일, 파일당 64 KiB, 총 2 MiB입니다. ZIP은 12 MiB, 내부 항목은 2,500개까지 받으며 압축 해제 전에 읽기 예산을 적용합니다. 문서·테스트·빌드 결과·비밀 파일은 제외합니다. 제한·생략·실패는 결과에 표시합니다.
'''),
(63,63, r'''
## v0.3 실제 소스 인수 검사

```bash
python scripts/capture_reference.py --output evidence/reference/snapshot.json
python scripts/acceptance_flow.py --snapshot evidence/reference/snapshot.json
python scripts/process_browser.py --snapshot evidence/reference/snapshot.json --url http://127.0.0.1:8000
python scripts/build_review_demo.py evidence/acceptance/analysis.json demo.html
```

`process_browser.py`는 실행 중인 서버를 사용합니다. `--bridge`는 명시적인 TestClient 대체 검사이며 일반 HTTP 검증으로 부르지 않습니다. 새 데모는 실제 분석 JSON을 동일한 화면으로 재생합니다. [v0.3 계약](docs/CYCLE_04_CONTRACT.md)을 기준으로 의미 검사와 화면 검사를 분리합니다.
'''),
]),
('docs/CORRECTIONS.md', '805589b79ad6fa38f617770ce5b7c103a5ff6a4d3b5c1f5fc39feea62681d259', '9cec65d326523473e44dda905d37c709eaa2d1a8a3e193732837326dd07ecf49', [
(0,0, r'''# v0.3 수정 기록 — Cycle 04

1. 파일 주변을 넓게 따라가던 Feature Flow 대신 라우트·함수 본문을 분리했다. Health 관련 파일 26개 문제를 1개로 축소하는 회귀 테스트를 추가했다.
2. 16개 파일 중심 추천도를 처리 단계 묶음으로 바꾸고, 클릭하면 같은 소스 그래프의 함수 내부와 줄 근거로 내려가도록 했다.
3. PIN/refresh는 별도 API 변형, SDK 로그인/가입/로그아웃은 별도 기능으로 분리했다.
4. 실제 추천 코드에서 안전 확인이 등급 분류보다 먼저라는 읽기 순서를 유지했다. 보기 좋게 업무 순서를 재배치하지 않았다.
5. 동명 전역 함수·임의 객체 메서드·중첩 선언을 잘못 연결하지 않는 검사를 추가했다. 명시적 연결도 정적 후보로 남긴다.
6. 추가 검사에서 `/destroy()/` 정규식 리터럴을 호출로 오인하는 실패 1건을 재현했다. 일반적인 정규식 시작 위치를 마스킹해 재통과시켰다. 이는 완전한 JS 문법 지원을 뜻하지 않는다.
7. 브라우저 검사에서 같은 기능의 버튼 2개를 선택하는 strict locator 오류를 발견해 선택자를 toolbar로 한정했다. 제품 로직이나 보안 정책을 약화하지 않았다.
8. GitHub 48파일 제한을 공통 160파일 예산으로 올렸다. 파일당 64 KiB/총 2 MiB, 부분 분석과 실패 표시는 유지했다.

---

## 이전 사이클 기록

'''),
]),
('docs/IMPROVEMENTS.md', 'eacd6294d8b08a15420be6e476e62b29fee6247219e380d8cf518dbe9852a97a', 'b9518b4debdae9a58c2b1be3c6981e39c0c7cfa2e8c822c5b96f993334ee5e1b', [
(0,1, r'''# v0.3 다음 개선
'''),
(2,3, r'''## 반영
전체 구조 → API/SDK 처리 요약 → 정적 호출 후보 내부 → 코드 근거. Health의 무관한 import 확장 제거. 실제 인증 경로 분리. 외부 기본 URL은 후보로 표시. GitHub도 160파일 예산을 사용한다.
'''),
(4,5, r'''## 남은 범위
- 제어 흐름 그래프(CFG): 분기/예외/비동기를 실제 제어 관계로 표시. 현재 화살표는 소스 읽기 순서다.
- 언어별 parser를 이용한 DI, 재수출, 별칭, 문자열 보간, router prefix 해석.
- 단계 이름의 의미 평가: 현재 규칙 기반 해석이며 잘못 분류할 수 있다.
- 모노레포, 큰 저장소, 비표준 프레임워크에 대한 정확도 검증.
'''),
(6,19, r'''## 반복 절차
실패 재현 테스트 → 최소 수정 → pytest/Skills/JS → 의미 인수 검사 → 실제 HTTP/ZIP/브라우저 → GitHub CI → MD 기록. 검사 통과를 전체 언어 지원 또는 runtime 증명으로 바꾸지 않는다.
'''),
]),
]
notice='''> **v0.3 갱신:** 아래 초기 설계 중 파일 중심 Feature Flow는 `docs/CYCLE_04_CONTRACT.md`로 대체합니다. 현재 계약은 schema 1.1: System Flow → API/SDK 본문 처리 단계 → 함수 내부/근거. 파일 그래프는 보조 보기입니다. 제품 파이프라인의 BUILD에서 `process.py`가 같은 근거 그래프에 본문 범위를 투영합니다. 단계 이름은 규칙 기반 해석, 선은 소스 읽기 순서, 호출 대상은 정적 후보입니다. 실제 실행/성공을 증명하지 않습니다. GitHub 수집 예산은 160파일(총 2 MiB)입니다.

'''
for name,before,after in [
('docs/ARCHITECTURE.md','9fd30071543cf2eba6772f90f584062f0987ee86c428f99df8adfd2b8275b90f','a489a83a89a5fe6b19caff1d6bd4defb6e8cc3c27e17ffc4681cd9f2e15a9188'),
('docs/CODEX_HANDOFF.md','efaae9b8f75bb0d963a5b477cffcf1cc8dc43d562eadbb61fbeba83f9d859bb6','04322c3f06ebe01f5a5a43b7911b75ca72631880ed1b8089d7722594a99952f6'),
('docs/CONTRACTS.md','17bb3712574c1356effc46094a9c89e3dfd14904bd3ea350cf2148a827cacf68','384fd5692d8ebfbe97c5c969eee361846de686ca324547ac2348c2fbdd9e9fbc'),
('docs/ORCHESTRATION.md','1bac1114d348c2c3be29300f4a89be71d7b7cbb8f78632c50760b36450f15baf','c5f4d59c1c38896be6672547aa1d219eff5b925ecd50024610fb78aba55f45ed'),
('docs/PROJECT.md','dd514be83a5bfd1177e92e8240022f0d17784b7cc51c69a98203439f0e62457d','706790c065b0126e5ef1bed98afdb6b8426bd4135044f566c597b9b531b2258b')]:EDITS.append((name,before,after,[(0,0,notice)]))
staged={}
for name,before,after,edits in EDITS:
    path=Path(name);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()==after:continue
    assert hashlib.sha256(raw).hexdigest()==before, 'Unexpected source: '+name
    lines=raw.decode('utf-8').splitlines(keepends=True)
    for start,end,value in reversed(edits):lines[start:end]=[value]
    result=''.join(lines).encode('utf-8')
    assert hashlib.sha256(result).hexdigest()==after, 'Edited content mismatch: '+name
    staged[path]=result
for path,result in staged.items():path.write_bytes(result)
print('Applied',len(staged),'checksum-verified source changes')
