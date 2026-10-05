from app.intake import load_demo
from app.extractor import extract_facts
from app.graph import build_analysis
from app.verifier import verify_analysis

def analyze(name='mobile'):
    snapshot = load_demo(name)
    facts, evidence, warnings = extract_facts(snapshot)
    result = build_analysis(snapshot, facts, evidence, warnings)
    verify_analysis(result, snapshot)
    return result

def test_system_then_feature_share_canonical_graph():
    result = analyze()
    assert len(result.system_nodes) <= 9
    assert {'Flutter App', 'Riverpod / Controller', 'Service / Dio', 'Hono Backend', 'Supabase'} <= {n.label for n in result.system_nodes}
    all_nodes = {n.id for n in result.nodes}
    all_edges = {e.id for e in result.edges}
    components = {n.id for n in result.system_nodes}
    assert len(result.features) >= 3
    for feature in result.features:
        assert set(feature.node_ids) <= all_nodes
        assert set(feature.edge_ids) <= all_edges
        assert set(feature.component_ids) <= components

def test_http_is_candidate_never_runtime_proof():
    result=analyze()
    matches=[e for e in result.edges if e.relation=='http-contract']
    assert matches and all(e.confidence=='candidate' for e in matches)

def test_python_demo_not_hardcoded_flutter():
    result=analyze('python')
    labels={n.label for n in result.system_nodes}
    assert 'FastAPI Backend' in labels
    assert 'Flutter App' not in labels
    assert any(e.parser=='ast' for e in result.evidence)

def test_infrastructure_not_double_counted():
    result=analyze()
    assert len([n for n in result.system_nodes if n.label=='Supabase'])==1
    assert not any('PostgreSQL' in n.label for n in result.system_nodes)
