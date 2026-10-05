# 데이터 계약 / 구현 기준

`SourceFile(path, content)`는 비신뢰 입력이다. path는 상대 POSIX 경로이며 `..`, absolute, URL, NUL, 숨김/비밀 파일을 거부한다.
`Snapshot`은 source files + origin + commit/snapshot hash + coverage를 가진다.
`Evidence(id, path, line, end_line, snippet, kind, parser)`는 항상 실제 파일 범위와 일치한다.
`FactSet`은 imports/routes/requests/symbols/infrastructure references를 가진다.
`FileNode`는 canonical node이며 `component_id`를 가진다.
`Edge`는 source/target + relation + confidence + evidence_ids를 가진다.
`SystemNode`는 FileNode 또는 infrastructure node의 투영이다. 예시의 고정 기술 스택을 하드코딩하지 않는다.
`Feature`는 endpoint + canonical node/edge IDs의 부분집합이다. 별도 창조한 그래프가 아니다.
`Analysis`는 schema_version, snapshot, coverage, facts, nodes, edges, system_nodes, system_edges, features, warnings, stages, optional explanation을 가진다.

## confidence 의미
- confirmed: import/route/sdk 등 정적 패턴이 실제 코드에 존재한다.
- candidate: 연결 해석에 추론이 들어간다(HTTP method/path 일치, runtime 미검증).
- unknown: 연결로 그리지 않고 warning으로 남긴다.

## API
GET /api/health — 버전/선택적 AI 사용 가능 여부. 키는 절대 반환 안 함.
POST /api/analyze — {source: demo|github|files, demo: mobile|python, url?, files?, explain: false}
POST /api/analyze-zip — raw application/zip 본문; filename, explain 선택 query. 동일 Snapshot 파이프라인 사용.
GET /api/demo/{mobile|python} — 합성 fixture 파일만 반환.
GET / — 정적 브라우저 UI.

## ZIP coverage
압축 해제 전에 읽기 예산을 제한한다. 파일 항목 집계: discovered = analyzed + skipped + omitted + failed. partial=false는 지원·선택 대상에서 생략과 실패가 없다는 의미이며 모든 저장소 파일을 분석했다는 뜻이 아니다.

## 공격/회귀 사례
가짜 URL / path traversal / `.env` / 주석 속 import / 문자열 속 가짜 코드 / undefined endpoint / AI의 가짜 ID / truncation / 서버가 다른데 같은 HTTP path / Supabase와 Postgres의 무근거 합치기.
