# FlowLens v0.2.0 수정 기록

검증 과정에서 실제로 발견한 문제와 수정 내용을 기록한다.

## 1. ZIP 입력 경로 부재

### 문제
기존 v0.1은 공개 GitHub URL과 브라우저 폴더 선택만 지원했다. 사용자가 일반적으로 전달하는 GitHub 다운로드 ZIP이나 프로젝트 ZIP을 직접 넣을 수 없었다.

### 수정
- `/api/analyze-zip` 추가
- UI에 `ZIP 선택` 버튼 추가
- ZIP 공통 최상위 폴더(`repo-main/`) 자동 제거
- 기존과 동일한 `INTAKE → EXTRACT → BUILD → VERIFY → EXPLAIN` 파이프라인 재사용

## 2. ZIP 안전성 경계 부족

### 문제
ZIP을 단순 압축 해제하면 path traversal, symlink, 과도한 파일 수/크기 문제가 생길 수 있다.

### 수정
- 디스크에 압축 해제하지 않고 메모리에서 읽음
- `..`, 절대 경로, 제어문자 경로 거부
- 암호화 ZIP 거부
- symlink 무시
- ZIP 최대 12 MiB
- 내부 파일 최대 2,500개 검사
- 단일 archive member 256 KiB 초과 제외
- 실제 분석 파일은 기존 64 KiB / 총 2 MiB 제한 유지

## 3. 분석 파이프라인 중복 가능성

### 문제
새 입력 유형을 추가할 때 GitHub/폴더/ZIP마다 EXTRACT 이후 로직을 복제하면 결과 계약이 갈라질 위험이 있었다.

### 수정
`analyze_snapshot()`을 분리해 모든 입력을 `Snapshot`으로 정규화한 뒤 같은 분석 파이프라인을 사용하게 했다.

```text
GitHub ─┐
Folder ─┼→ Snapshot → EXTRACT → BUILD → VERIFY → EXPLAIN
ZIP ────┘
```

## 4. 버전 표시 불일치

### 문제
패키지 버전만 올리고 결과 JSON의 `analyzer_version`을 그대로 두면 API 응답과 서버 health 버전이 다르게 보일 수 있었다.

### 수정
서버 버전과 analyzer 결과 버전을 모두 `0.2.0`으로 맞췄다.

## 5. 실제 GitHub 검증 표현 과장 가능성

### 문제
v0.1 문서에는 GitHub 네트워크 분석이 실제로 실행되지 않았다고 적혀 있었지만, 실제 저장소 구조 검증과 앱 프로세스의 live HTTP 검증이 명확히 분리되지 않았다.

### 수정
`EXECUTION_VALIDATION.md`에서 다음을 분리했다.

- 연결된 GitHub를 통해 실제 `vibecare-pilot` tree/파일 확인: PASS
- GitHub API 로직 Mock E2E: PASS
- 현재 sandbox 앱 프로세스 → api.github.com DNS 연결: ENVIRONMENT BLOCKED

## 6. 테스트 수와 README 상태 불일치

### 문제
README의 59개 테스트 기록이 새 기능 추가 뒤 실제 상태와 달랐다.

### 수정
현재 기록을 64개 자동 테스트 통과로 갱신하고 ZIP·GitHub 검증 상태를 함께 명시했다.

## 남아 있는 수정 후보

다음 항목은 이번 사이클에서 발견했지만 아직 구현하지 않았다.

1. Hono router prefix와 동적 path parameter의 더 정확한 결합
2. Dart/Dio의 문자열 보간 URL 추적
3. 큰 저장소에서 48개 파일을 중요도 기반으로 더 정교하게 선택
4. 함수 호출 수준 Feature Trace
5. 네트워크 허용 환경에서 live GitHub end-to-end 캡처
