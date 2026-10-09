"""UML acceptance on source strings ONLY. Never execute these target snippets."""
import copy
import pytest
from tests.test_process_flow import analyze
from app.verifier import VerificationError, verify_analysis

PY_HEAD="from fastapi import FastAPI\napp=FastAPI()\n@app.get('/demo')\ndef demo(data=None):\n"
JS_HEAD="import { Hono } from 'hono';\nconst app=new Hono();\napp.get('/demo', (c) => {\n"

def result_for(body, lang='py'):
    text=PY_HEAD+body if lang=='py' else JS_HEAD+body+'\n});'
    result,snapshot=analyze([('backend/main.'+lang,text)])
    flow=next(f for f in result.flows if f.kind=='route')
    return result,snapshot,flow

def activity(body,lang='py'):
    return result_for(body,lang)[2].activity

def reachable(a,source,target):
    todo=[source];seen=set()
    while todo:
        here=todo.pop()
        if here==target:return True
        if here in seen:continue
        seen.add(here);todo.extend(e.target for e in a.edges if e.source==here)
    return False

@pytest.mark.parametrize('lang,body',[
 ('py','    if data is None:\n        raise ValueError("missing")\n    value=calculate(data)\n    return value\n'),
 ('ts','  if (!c) { throw new Error("missing"); }\n  const value=calculate(c);\n  return value;'),
 ('js','  if (!c) throw new Error("missing");\n  const value=calculate(c);\n  return value;'),
])
def test_exception_branch_never_reaches_normal_calculation(lang,body):
    a=activity(body,lang)
    assert a.status=='supported-subset'
    decision=next(n for n in a.nodes if n.kind=='decision')
    assert {e.guard for e in a.edges if e.source==decision.id}=={'true','false'}
    throw=next(n for n in a.nodes if n.kind=='raise')
    calc=next(n for n in a.nodes if 'calculate(' in n.label)
    assert not reachable(a,throw.id,calc.id)
    assert all(e.relation=='control-flow' and e.confidence=='static-candidate' for e in a.edges)
    assert a.runtime_verified is False

@pytest.mark.parametrize('lang,body',[
 ('py','    if data:\n        return 1\n    else:\n        raise ValueError()\n    never()\n'),
 ('ts','  if (c) return 1; else throw new Error();\n  never();'),
])
def test_both_exits_do_not_get_false_merge_or_unreachable_action(lang,body):
    a=activity(body,lang)
    assert a.status=='supported-subset'
    assert not any('never(' in n.label or n.kind=='merge' for n in a.nodes)
    assert any('unreachable' in w for w in a.warnings)
    for n in a.nodes:
        if n.kind in {'return','raise'}:
            assert all(next(x for x in a.nodes if x.id==e.target).kind in {'final','exception-final'} for e in a.edges if e.source==n.id)

@pytest.mark.parametrize('lang,body',[
 ('py','    if data:\n        value=1\n    else:\n        value=2\n    return value\n'),
 ('ts','  if (c) { value=1; } else { value=2; }\n  return value;'),
])
def test_branches_merge_only_when_both_continue(lang,body):
    a=activity(body,lang)
    merge=next(n for n in a.nodes if n.kind=='merge')
    assert len([e for e in a.edges if e.target==merge.id])==2
    assert len([e for e in a.edges if e.source==merge.id])==1

@pytest.mark.parametrize('body',[
 '    for item in data:\n        save(item)\n    return 1\n',
 '    try:\n        return 1\n    finally:\n        cleanup()\n',
 '    with manager():\n        return 1\n',
 '    value=(yield data)\n    return value\n',
 '    match data:\n        case 1:\n            return 1\n    return 2\n',
])
def test_unsupported_python_is_explicit_fallback_not_a_linear_cfg(body):
    r,_,f=result_for(body)
    a=f.activity
    assert a.status=='unsupported' and a.reason
    assert not a.nodes and not a.edges
    assert f.order=='source-order' and f.steps

@pytest.mark.parametrize('body',[
 '  try { return 1; } finally { cleanup(); }',
 '  for (const x of items) { save(x); } return 1;',
 '  switch(c) { case 1: return 2; }',
 '  return\n  calculate();',
 '  const value=1\n  return value;',
 '  const callback=()=>{ throw new Error(); }; return callback();',
])
def test_unsupported_lexical_grammar_fails_closed(body):
    a=activity(body,'ts')
    assert a.status=='unsupported' and a.reason and not a.edges

def test_dict_get_keeps_unknown_meaning_in_both_views():
    r,_,f=result_for("    cache={}\n    value=cache.get('answer')\n    return value\n")
    assert f.activity.status=='supported-subset'
    n=next(n for n in f.activity.nodes if 'cache.get' in n.label)
    assert n.semantic_status=='unknown'
    assert not any(s.category=='network' for s in f.steps)

def test_activity_reuses_flow_membership_and_registered_evidence():
    r,s,f=result_for('    if data:\n        return 1\n    return 2\n')
    a=f.activity;ev={e.id:e for e in r.evidence}
    for n in a.nodes:
        assert n.evidence_ids and set(n.evidence_ids)<=set(f.evidence_ids)
        assert set(n.node_ids)<=set(f.node_ids)
        assert all(ev[e].path==f.path for e in n.evidence_ids)
    verify_analysis(r,s)

@pytest.mark.parametrize('corruption',['dangling','exit-edge','guard','evidence','status'])
def test_verifier_rejects_corrupted_control_flow(corruption):
    r,s,f=result_for('    if data:\n        return 1\n    return 2\n')
    a=f.activity
    if corruption=='dangling':a.edges[0].target='invented'
    if corruption=='guard':
        d=next(n for n in a.nodes if n.kind=='decision')
        next(e for e in a.edges if e.source==d.id).guard=''
    if corruption=='exit-edge':
        e=copy.deepcopy(a.edges[0]);e.id='invalid';e.source=next(n.id for n in a.nodes if n.kind=='final');a.edges.append(e)
    if corruption=='evidence':a.nodes[1].evidence_ids=['invented']
    if corruption=='status':a.status='unsupported'
    with pytest.raises(VerificationError):verify_analysis(r,s)

def test_elif_guards_and_nested_returns():
    a=activity('    if data==1:\n        return 1\n    elif data==2:\n        return 2\n    else:\n        value=3\n    return value\n')
    assert len([n for n in a.nodes if n.kind=='decision'])==2
    assert not any(n.kind=='merge' for n in a.nodes)

def test_dependency_call_and_control_flow_not_conflated():
    r,_,f=result_for('    return helper(data)\n')
    assert all(e.relationship_kind in {'dependency','reference'} for e in r.edges)
    assert all(c.relation=='call' for s in f.steps for c in s.calls)
    assert all(e.relation=='control-flow' for e in f.activity.edges)


def test_ui_helpers_use_guarded_solid_arrows_and_escape_source():
    import json,subprocess
    r,_,_=result_for('    if data:\n        return "<img onerror=evil()>"\n    raise ValueError("bad")\n')
    run=subprocess.run(['node','tests/uml_view.cjs'],input=r.model_dump_json(),text=True,capture_output=True)
    assert run.returncode==0,run.stderr
    view=json.loads(run.stdout)
    assert '<polygon' in view['svg'] and '<circle' in view['svg']
    assert 'stroke-dasharray' not in view['svg']
    assert '<img' not in view['svg'] and '&lt;img' in view['svg']
    assert '-->|true|' in view['mermaid'] and '-->|false|' in view['mermaid']
    assert len(view['positions'])==len(view['nodes'])
    for _,p in view['positions']:
        assert 0<=p['x']<view['w'] and p['x']+p['w']<=view['w']
        assert 0<=p['y']<view['h'] and p['y']+p['h']<=view['h']


def test_activity_export_not_source_order_and_previous_view_preserved():
    from pathlib import Path
    source=Path('static/app.js').read_text()
    assert 'data-detail="activity"' in source
    assert 'function renderActivityPanel(' in source
    assert 'function activityMermaid(' in source
    assert 'function processGraph(' in source

@pytest.mark.parametrize('condition',['(yield data)', '[x for x in data]'])
def test_python_hidden_control_in_condition_falls_back(condition):
    a=activity(f'    if {condition}:\n        return 1\n    return 0\n')
    assert a.status=='unsupported'


def test_lexical_missing_semicolon_between_assignments_falls_back():
    a=activity('  value=1\n  save(value);\n  return value;','ts')
    assert a.status=='unsupported'


def test_activity_node_budget_falls_back_without_partial_fake_chain():
    a=activity(''.join(f'    x{i}={i}\n' for i in range(135))+'    return 1\n')
    assert a.status=='unsupported' and not a.edges and '128' in a.reason


def test_nested_decision_does_not_jump_to_next_condition_on_return():
    a=activity('    if data:\n        if data==1:\n            return 1\n        value=2\n    else:\n        value=3\n    return value\n')
    ret=next(n for n in a.nodes if n.label=='return 1')
    update=next(n for n in a.nodes if n.label=='value=2')
    assert not reachable(a,ret.id,update.id)
    assert len([n for n in a.nodes if n.kind=='merge'])==1


def test_same_line_branch_call_not_attributed_to_condition():
    r,_,f=result_for('  if (c) return helper(c); return 0;','ts')
    a=f.activity
    assert not next(n for n in a.nodes if n.kind=='decision').call_refs
    ret=next(n for n in a.nodes if n.kind=='return' and 'helper' in n.label)
    assert ret.call_refs
    ref=ret.call_refs[0]
    step=next(s for s in f.steps if s.id==ref.step_id)
    assert step.calls[ref.call_index].name=='helper'


def test_call_relation_and_control_semantics_cannot_be_corrupted():
    r,s,f=result_for('    return helper(data)\n')
    f.steps[0].calls[0].relation='dependency'
    with pytest.raises(VerificationError):verify_analysis(r,s)


def test_call_ref_cannot_be_forged_from_same_line_other_branch():
    from app.models import ActivityCallRef
    r,s,f=result_for('  if (c) return helper(c); return 0;','ts')
    n=next(n for n in f.activity.nodes if n.kind=='decision')
    ret=next(n for n in f.activity.nodes if n.kind=='return' and n.call_refs)
    n.call_refs=[copy.deepcopy(ret.call_refs[0])]
    with pytest.raises(VerificationError):verify_analysis(r,s)
