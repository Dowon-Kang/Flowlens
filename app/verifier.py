"""Independent structural/evidence gate. Does not prove runtime correctness."""
from .models import Analysis, Snapshot

class VerificationError(ValueError):
    pass

def verify_analysis(result: Analysis, snapshot: Snapshot) -> None:
    files={f.path:f.content.splitlines() for f in snapshot.files}
    ev={e.id:e for e in result.evidence}
    if len(ev)!=len(result.evidence): raise VerificationError('중복 evidence ID')
    for e in result.evidence:
        lines=files.get(e.path)
        if lines is None or not (1<=e.line<=e.end_line<=len(lines)):
            raise VerificationError('근거 파일/줄 범위 오류')
        if '\n'.join(lines[e.line-1:e.end_line])!=e.snippet:
            raise VerificationError('근거 snippet과 실제 소스 불일치')
    nodes={n.id:n for n in result.nodes}; system={n.id:n for n in result.system_nodes}; edges={e.id:e for e in result.edges}
    if len(nodes)!=len(result.nodes) or len(system)!=len(result.system_nodes) or len(edges)!=len(result.edges):
        raise VerificationError('중복 graph ID')
    for n in result.nodes:
        if n.component_id not in system: raise VerificationError('상위 component 없음')
        if not n.evidence_ids or any(x not in ev for x in n.evidence_ids): raise VerificationError('노드 근거 없음')
        if n.id not in system[n.component_id].member_ids: raise VerificationError('부모/자식 membership 불일치')
    for n in result.system_nodes:
        if n.kind!='virtual' and (not n.evidence_ids or any(e not in ev for e in n.evidence_ids)):
            raise VerificationError('overview 노드 근거 없음')
        if n.kind!='virtual' and set(n.evidence_ids)!={e for i in n.member_ids for e in nodes[i].evidence_ids}:
            raise VerificationError('overview 근거 합계 불일치')
    members=[i for n in result.system_nodes for i in n.member_ids]
    if len(set(members))!=len(members) or set(members)!=set(nodes): raise VerificationError('overview membership 중복/누락')
    for graph_edges, graph_nodes in [(result.edges,nodes),(result.system_edges,system)]:
        for e in graph_edges:
            expected_kind='dependency' if e.relation in {'import','sdk'} else 'reference'
            if e.relationship_kind!=expected_kind:raise VerificationError('구성 관계를 실행 관계로 혼동함')
            if e.source not in graph_nodes or e.target not in graph_nodes: raise VerificationError('edge endpoint 없음')
            if not e.evidence_ids or any(x not in ev for x in e.evidence_ids): raise VerificationError('edge 근거 없음')
            if e.relation in {'http-contract','entry-model'} and e.confidence!='candidate': raise VerificationError('후보 관계를 사실로 승격함')
    for f in result.features:
        if not set(f.node_ids)<=set(nodes) or not set(f.edge_ids)<=set(edges): raise VerificationError('feature가 canonical graph 밖의 ID를 사용함')
        if not set(f.component_ids)<=set(system): raise VerificationError('feature의 상위 context 없음')
        for eid in f.edge_ids:
            if edges[eid].source not in f.node_ids or edges[eid].target not in f.node_ids: raise VerificationError('feature edge endpoint 누락')

    flows={f.id:f for f in result.flows}
    if len(flows)!=len(result.flows): raise VerificationError('중복 처리 지도 ID')
    step_ids=set()
    for flow in result.flows:
        if flow.path not in files or not (1<=flow.line<=flow.end_line<=len(files[flow.path])):
            raise VerificationError('처리 지도 범위 오류')
        if flow.order!='source-order': raise VerificationError('미검증 실행 순서')
        if not flow.node_ids or not set(flow.node_ids)<=set(nodes): raise VerificationError('처리 지도 파일 누락')
        if not flow.evidence_ids or not set(flow.evidence_ids)<=set(ev): raise VerificationError('처리 지도 근거 누락')
        previous=flow.line
        for step in flow.steps:
            if step.id in step_ids:raise VerificationError('중복 처리 단계 ID')
            step_ids.add(step.id)
            if not (flow.line<=step.line<=step.end_line<=flow.end_line) or step.line<previous:
                raise VerificationError('처리 단계 순서/범위 오류')
            previous=step.line
            if step.category=='unknown' and step.semantic_status!='unknown':
                raise VerificationError('미확인 의미를 확정 근거로 승격함')
            if step.semantic_status=='syntax' and step.category not in {'exception','response','prepare','condition'}:
                raise VerificationError('의미 해석 후보를 문법 근거로 과장함')
            if not step.evidence_ids or not set(step.evidence_ids)<=set(flow.evidence_ids):raise VerificationError('처리 단계 근거 누락')
            if not set(step.node_ids)<=set(flow.node_ids):raise VerificationError('처리 단계 소속 오류')
            for eid in step.evidence_ids:
                e=ev[eid]
                if e.path!=flow.path or not (step.line<=e.line<=step.end_line):raise VerificationError('처리 단계 범위 밖 근거')
            for call in step.calls:
                if call.relation!="call":raise VerificationError("호출 관계 유형 오류")
                if call.evidence_id not in step.evidence_ids:raise VerificationError('호출 위치 근거 없음')
                if not call.callee_id and (call.resolution!='unresolved' or call.resolution_basis!='unresolved'):
                    raise VerificationError('미확인 호출을 정적 연결로 승격함')
                if call.callee_id and (not call.resolution_reason or call.resolution_basis=='unresolved'):
                    raise VerificationError('호출 대상의 해석 근거가 없음')
                if call.callee_id and (call.callee_id not in flows or call.resolution!='static-candidate'):
                    raise VerificationError('호출 대상 없음/실행 확정 과장')
    from .activity import verify_activity
    for flow in result.flows:
        verify_activity(flow,ev)
    for feature in result.features:
        if not set(feature.flow_ids)<=set(flows):raise VerificationError('기능 처리 지도 누락')

    from .quality import quality_report
    quality, diagnostics = quality_report(result, snapshot)
    if result.analysis_quality != quality or result.diagnostics != diagnostics:
        raise VerificationError('읽기·파싱·미확인 진단 통계 불일치')
