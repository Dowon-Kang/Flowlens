"""Diagnostics over the existing snapshot/graph. Counts are not accuracy scores."""
from __future__ import annotations
import ast
from pathlib import PurePosixPath
from .models import Analysis, Snapshot, AnalysisQuality, AnalysisDiagnostic
from .intake import SOURCE_SUFFIXES


def quality_report(result: Analysis, snapshot: Snapshot) -> tuple[AnalysisQuality, list[AnalysisDiagnostic]]:
    q = AnalysisQuality()
    diagnostics = []
    for file in sorted(snapshot.files, key=lambda f: f.path):
        suffix = PurePosixPath(file.path).suffix.lower()
        if suffix not in SOURCE_SUFFIXES:
            q.manifest_files += 1
            continue
        q.source_files += 1
        if suffix == '.py':
            try:
                ast.parse(file.content)
                q.ast_files += 1
            except (SyntaxError, RecursionError, ValueError):
                q.parse_failed_files += 1
                diagnostics.append(AnalysisDiagnostic(code='parse-error', severity='warning', path=file.path,
                    message='파일은 읽었지만 Python AST 파싱에 실패했습니다. 해당 본문·호출은 해석하지 못했습니다.'))
        else:
            q.lexical_files += 1
    q.process_flows = len(result.flows)
    for flow in result.flows:
        for step in flow.steps:
            q.unknown_steps += step.semantic_status == 'unknown'
            for call in step.calls:
                q.calls += 1
                q.static_candidate_calls += bool(call.callee_id)
                q.unresolved_calls += not bool(call.callee_id)
    if q.lexical_files:
        diagnostics.append(AnalysisDiagnostic(code='lexical-only', severity='info',
            message='JS/TS/Dart는 제한된 패턴 분석입니다. 파싱 성공·완전한 타입/스코프 해석으로 간주하지 않습니다.'))
    if q.unresolved_calls:
        diagnostics.append(AnalysisDiagnostic(code='unresolved-calls', severity='info',
            message='추출된 처리 지도에서 대상 미확인 호출이 남아 있습니다. 외부 SDK·내장 함수도 포함할 수 있으며 정확도 점수가 아닙니다.'))
    return q, diagnostics
