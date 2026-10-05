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
            if e.source not in graph_nodes or e.target not in graph_nodes: raise VerificationError('edge endpoint 없음')
            if not e.evidence_ids or any(x not in ev for x in e.evidence_ids): raise VerificationError('edge 근거 없음')
            if e.relation in {'http-contract','entry-model'} and e.confidence!='candidate': raise VerificationError('후보 관계를 사실로 승격함')
    for f in result.features:
        if not set(f.node_ids)<=set(nodes) or not set(f.edge_ids)<=set(edges): raise VerificationError('feature가 canonical graph 밖의 ID를 사용함')
        if not set(f.component_ids)<=set(system): raise VerificationError('feature의 상위 context 없음')
        for eid in f.edge_ids:
            if edges[eid].source not in f.node_ids or edges[eid].target not in f.node_ids: raise VerificationError('feature edge endpoint 누락')
