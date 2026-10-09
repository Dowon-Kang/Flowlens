"""Cycle 05: semantic confidence failures and protected real HTTP clients.
All source strings are untrusted test data; they are parsed, never executed.
"""
import pytest
from tests.test_process_flow import analyze


def python_route(body, imports=''):
    return [('app/main.py', 'from fastapi import FastAPI\n'+imports+'\napp=FastAPI()\n@app.get("/answer")\ndef answer():\n'+''.join('    '+line+'\n' for line in body.splitlines()))]


def flow(result):
    return next(f for f in result.flows if f.kind == 'route')


def step_with_call(result, name):
    return next(s for s in flow(result).steps if any(c.name == name for c in s.calls))


def test_dictionary_get_is_unknown_not_external_request():
    result,_ = analyze(python_route("cache = {'answer': 42}\nvalue = cache.get('answer')\nreturn value"))
    s=step_with_call(result,'cache.get')
    assert s.category == 'unknown'
    assert s.semantic_status == 'unknown'
    assert '미확인' in s.label
    assert not [f for f in result.facts if f.kind == 'request']


@pytest.mark.parametrize('name', ['fetchAnswer','login','saveUser','calculateRecommendation','readRule'])
def test_unresolved_names_do_not_establish_business_meaning(name):
    result,_=analyze(python_route(f'value = {name}()\nreturn value'))
    s=step_with_call(result,name)
    assert s.category=='unknown'
    assert s.semantic_status=='unknown'


def test_unknown_call_not_merged_into_previous_known_operation():
    result,_=analyze(python_route("response = requests.get('https://example.test')\nvalue = cache.get('answer')\nreturn value", 'import requests'))
    assert step_with_call(result,'cache.get').category=='unknown'
    assert step_with_call(result,'requests.get').category=='network'
    assert step_with_call(result,'cache.get').id != step_with_call(result,'requests.get').id


@pytest.mark.parametrize('body', ['raise ValueError("bad")','raise'])
def test_python_raise_is_exception_not_return(body):
    result,_=analyze(python_route(body))
    s=flow(result).steps[0]
    assert s.category=='exception'
    assert s.semantic_status=='syntax'
    assert '반환' not in s.label


@pytest.mark.parametrize('statement', ['throw new Error("bad");','throw failure;'])
def test_javascript_throw_is_exception_not_return(statement):
    result,_=analyze([('app/main.ts', "import { Hono } from 'hono';\nconst app=new Hono();\napp.get('/answer', c => {"+statement+"});")])
    assert flow(result).steps[0].category=='exception'


def test_keyword_prefix_is_not_a_return_or_throw():
    result,_=analyze(python_route('returnValue()\nthrowError()\nreturn 1'))
    assert step_with_call(result,'returnValue').category=='unknown'
    assert step_with_call(result,'throwError').category=='unknown'


@pytest.mark.parametrize('imports,body,name', [
    ('import requests', "v = requests.get('https://example.test')", 'requests.get'),
    ('import httpx', "v = httpx.post('https://example.test')", 'httpx.post'),
    ('import httpx as hx', "v = hx.get('https://example.test')", 'hx.get'),
    ('from requests import get as request_get', "v = request_get('https://example.test')", 'request_get'),
    ('import requests', "session = requests.Session()\nv = session.get('https://example.test')", 'session.get'),
    ('import httpx', "client = httpx.Client()\nv = client.get('https://example.test')", 'client.get'),
])
def test_import_and_construction_supported_http_clients(imports,body,name):
    result,_=analyze(python_route(body+'\nreturn v',imports))
    assert step_with_call(result,name).category=='network'
    assert step_with_call(result,name).semantic_status=='candidate'
    assert any(f.kind=='request' and f.value=='https://example.test' for f in result.facts)


@pytest.mark.parametrize('binding', ['client','session','requests','httpx'])
def test_client_like_name_or_shadowed_import_is_not_http(binding):
    result,_=analyze(python_route(f"{binding} = {{'answer': 42}}\nv = {binding}.get('https://example.test')\nreturn v",'import requests\nimport httpx'))
    assert step_with_call(result,f'{binding}.get').category=='unknown'
    assert not [f for f in result.facts if f.kind=='request']


def test_http_alias_shadowed_by_parameter_is_unknown():
    result,_=analyze([('app/main.py','''from fastapi import FastAPI
import httpx as client
app=FastAPI()
@app.get('/x')
def x(client):
    value = client.get('https://example.test')
    return value
''')])
    assert step_with_call(result,'client.get').category=='unknown'
    assert not [f for f in result.facts if f.kind=='request']


def test_async_context_manager_client_is_still_http():
    result,_=analyze([('app/main.py','''from fastapi import FastAPI
import httpx
app=FastAPI()
@app.get('/x')
async def x():
    async with httpx.AsyncClient() as session:
        value = await session.get('https://example.test')
    return value
''')])
    assert step_with_call(result,'session.get').category=='network'
    assert any(f.kind=='request' for f in result.facts)


@pytest.mark.parametrize('imports,body,name', [
    ('', "const value = await fetch('/answer');", 'fetch'),
    ("import axios from 'axios';", "const value = await axios.get('/answer');", 'axios.get'),
])
def test_real_js_http_patterns_preserved(imports,body,name):
    result,_=analyze([('app/main.ts', "import { Hono } from 'hono';\n"+imports+"\nconst app = new Hono();\napp.get('/answer', async c => { "+body+" return c.json(value); });")])
    assert step_with_call(result,name).category=='network'
    assert any(f.kind=='request' for f in result.facts)


def test_resolved_named_helper_keeps_candidate_not_proven_meaning():
    from tests.test_process_flow import SAMPLE
    result,_=analyze(SAMPLE)
    s=next(s for f in result.flows for s in f.steps if any(c.name=='calculateRecommendation' for c in s.calls))
    assert s.category=='recommend'  # navigation label retained, not a fact about runtime.
    assert s.semantic_status=='candidate'
    assert '실행 미검증' in s.description

@pytest.mark.parametrize('body,name', [
    ("const client = {get: () => 1}; const v = client.get('/answer');", 'client.get'),
    ("const axios = {get: () => 1}; const v = axios.get('/answer');", 'axios.get'),
])
def test_javascript_import_does_not_make_unrelated_dictionary_a_client(body,name):
    result,_=analyze([('app/main.ts', "import { Hono } from 'hono';\nimport axios from 'axios';\nconst app=new Hono();\napp.get('/answer', c => {"+body+" return c.json(v); });")])
    assert step_with_call(result,name).category=='unknown'
    assert not [f for f in result.facts if f.kind=='request']


def test_js_axios_created_client_retains_http_candidate():
    result,_=analyze([('app/main.ts', "import { Hono } from 'hono';\nimport axios from 'axios';\nconst client=axios.create();\nconst app=new Hono();\napp.get('/answer', async c => { const v=await client.get('/real');return c.json(v); });")])
    assert step_with_call(result,'client.get').category=='network'
    assert any(f.kind=='request' and f.value=='/real' for f in result.facts)


def test_unknown_semantic_status_cannot_be_promoted_by_the_gate():
    from app.verifier import VerificationError,verify_analysis
    result,snapshot=analyze(python_route("cache = {}\nv = cache.get('answer')\nreturn v"))
    step_with_call(result,'cache.get').semantic_status='syntax'
    with pytest.raises(VerificationError):
        verify_analysis(result,snapshot)


def test_implicit_arrow_return_is_syntax_not_a_guess_from_method_name():
    result,_=analyze([('app/main.ts', "import { Hono } from 'hono';\nconst app=new Hono();\napp.get('/health', c => computeValue());")])
    assert flow(result).steps[0].category=='response'
    assert flow(result).steps[0].semantic_status=='syntax'
    assert not flow(result).steps[0].calls[0].callee_id
