"""Acceptance tests: output meaning, not merely clickability."""
import pytest
from app.intake import from_files
from app.models import SourceFile
from app.extractor import extract_facts
from app.graph import build_analysis
from app.verifier import verify_analysis, VerificationError

def analyze(files):
    s=from_files([SourceFile(path=p,content=c) for p,c in files])
    facts,ev,w=extract_facts(s); r=build_analysis(s,facts,ev,w);verify_analysis(r,s)
    return r,s

SAMPLE=[('backend/index.ts', '''import { Hono } from 'hono';
import { calculateRecommendation } from './algorithm.js';
import { getUser } from './unrelated.js';
const app = new Hono();
app.get('/health', c => c.json({ok: true}));
app.post('/recommendations', async (c) => {
  const body = await c.req.json();
  if (!body.ok) return c.json({error: 'INVALID'}, 400);
  const result = calculateRecommendation(body);
  return c.json(result);
});
app.get('/users', c => getUser());
'''),('backend/algorithm.ts', '''export function calculateRecommendation(input: unknown) {
  const valid = validateMeasurement(input);
  if (!valid) return null;
  const level = classifyMuscle(input);
  return {level};
}
function validateMeasurement(input: unknown) { return Boolean(input); }
function classifyMuscle(input: unknown) { return 'low'; }
'''),('backend/unrelated.ts', 'export function getUser() { return {id: 1}; }')]

def test_route_scoped_health_not_import_neighborhood():
    r,_=analyze(SAMPLE);f=next(f for f in r.features if f.label=='Health')
    assert len(f.node_ids)==1
    assert f.flow_ids
    flow=next(x for x in r.flows if x.id==f.flow_ids[0]);assert len(flow.steps)==1
    assert all('algorithm' not in n.path for n in r.nodes if n.id in f.node_ids)

def test_summary_and_function_expansion_have_real_scope():
    r,_=analyze(SAMPLE);f=next(f for f in r.features if f.label=='추천')
    flow=next(x for x in r.flows if x.id==f.flow_ids[0])
    assert any(s.label=='추천 계산' for s in flow.steps)
    call=next(c for s in flow.steps for c in s.calls if c.name=='calculateRecommendation')
    target=next(x for x in r.flows if x.id==call.callee_id)
    assert target.label=='calculateRecommendation'
    assert any('검증' in s.label for s in target.steps)
    assert any('분류' in s.label for s in target.steps)
    assert all(n.path!='backend/unrelated.ts' for n in r.nodes if n.id in f.node_ids)

def test_comments_strings_and_unrelated_methods_do_not_become_call_edges():
    r,_=analyze([('backend/main.ts', '''import { Hono } from 'hono';
const app = new Hono();
function calculate() { return 9; }
app.get('/x', c => {
  // calculate();
  const text = "calculate()";
  other.calculate();
  return c.json(text);
});''')])
    flow=next(x for x in r.flows if x.kind=='route')
    assert not [c for s in flow.steps for c in s.calls if c.callee_id]

def test_multiple_endpoints_separate_variants():
    r,_=analyze([('backend/a.py', '''from fastapi import FastAPI
app = FastAPI()
@app.get('/auth/login')
def login():
    return {'login': True}
@app.post('/auth/refresh')
def refresh():
    return {'refresh': True}
''')])
    assert len(r.features[0].flow_ids)==2
    assert len({next(x for x in r.flows if x.id==i).line for i in r.features[0].flow_ids})==2

def test_direct_sdk_auth_is_its_own_feature():
    r,_=analyze([('mobile/services/auth.dart', '''import 'package:supabase_flutter/supabase_flutter.dart';
Future<void> login() async {
  await Supabase.instance.client.auth.signInWithPassword(email: email, password: password);
}
''')])
    assert any('Supabase' in f.label for f in r.features)

def test_verifier_rejects_forged_step_evidence():
    r,s=analyze(SAMPLE);r.flows[0].steps[0].evidence_ids=['invented']
    with pytest.raises(VerificationError):verify_analysis(r,s)

def test_python_nested_function_body_not_claimed_as_executed():
    r,_=analyze([('backend/a.py', '''from fastapi import FastAPI
app = FastAPI()
def destroy(): return None
@app.get('/health')
def health():
    def later():
        destroy()
    return {'ok': True}
''')])
    flow=next(x for x in r.flows if x.kind=='route')
    assert not [c for s in flow.steps for c in s.calls if c.name=='destroy']

def test_constructor_method_does_not_resolve_global_same_name():
    r,_=analyze([('backend/app.ts', '''import { Hono } from 'hono';
function measure() { return 99; }
const app = new Hono();
app.post('/measure', c => new Unknown().measure());
''')])
    flow=next(f for f in r.flows if f.kind=='route')
    assert not [c for s in flow.steps for c in s.calls if c.callee_id]

def test_constructor_import_method_can_expand_as_candidate():
    r,_=analyze([('backend/app.ts', '''import { Hono } from 'hono';
import { Provider } from './provider.js';
const app = new Hono();
app.post('/measure', c => new Provider().measure());
'''),('backend/provider.ts', '''export class Provider {
  async measure() { return fetch('https://example.test'); }
}
''')])
    flow=next(f for f in r.flows if f.kind=='route')
    call=next(c for s in flow.steps for c in s.calls if c.name=='new:Provider.measure')
    assert call.callee_id and call.resolution=='static-candidate'

def test_default_url_is_not_a_proven_network_request():
    r,_=analyze([('backend/provider.ts', '''class Provider {
 constructor(private readonly baseUrl = 'https://api.example.test') {}
}
''')])
    edge=next(e for e in r.edges if e.relation=='config-url')
    assert edge.confidence=='candidate'

def test_regex_literal_is_not_a_function_call():
    r,_=analyze([('backend/app.ts', """import { Hono } from 'hono';
function destroy() { return 1; }
const app = new Hono();
app.get('/health', c => { const pattern = /destroy()/; return c.json({ok: true}); });
""")])
    flow=next(f for f in r.flows if f.kind=='route')
    assert not [c for s in flow.steps for c in s.calls if c.name=='destroy']

def test_python_shadowed_import_is_unresolved():
    r,_=analyze([('backend/app.py', """from fastapi import FastAPI
from logic import calculate
app=FastAPI()
@app.get('/x')
def x():
    calculate = lambda: 99
    return calculate()
"""),('backend/logic.py','def calculate(): return 42')])
    flow=next(f for f in r.flows if f.kind=='route')
    assert all(not c.callee_id for s in flow.steps for c in s.calls if c.name=='calculate')

def test_python_comment_does_not_classify_health_as_safety():
    r,_=analyze([('backend/app.py', """from fastapi import FastAPI
app=FastAPI()
@app.get('/health')
def health():
    # if safetyBlocked: return False
    ready = True
    return {'ok': ready}
""")])
    flow=next(f for f in r.flows if f.kind=='route')
    assert all(s.category!='safety' for s in flow.steps)
