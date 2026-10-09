"""Source strings are data. No target module import, eval, network or execution."""
import asyncio
import base64
import io
import zipfile
import httpx
import pytest
from app.models import SourceFile
from app.intake import GitHubReader, from_files, from_zip_bytes, MAX_FILE_BYTES, MAX_TOTAL_BYTES
from app.verifier import VerificationError, verify_analysis
from tests.test_process_flow import analyze

HEADER = "from fastapi import FastAPI\napp=FastAPI()\n"
HELPER = "def save(value):\n    return value\n"


def get_call(result, name):
    return next(c for f in result.flows if f.kind=='route' for s in f.steps for c in s.calls if c.name==name)


@pytest.mark.parametrize('imp,call', [
    ('import pkg.logic as svc', 'svc.save'),
    ('from pkg import logic as svc', 'svc.save'),
    ('import pkg.logic', 'pkg.logic.save'),
    ('from .logic import save as store', 'store'),
])
def test_python_explicit_module_and_symbol_alias_navigation(imp,call):
    text=HEADER+imp+"\n@app.get('/item')\ndef item():\n    value = "+call+"(1)\n    return value\n"
    r,_=analyze([('pkg/main.py',text),('pkg/logic.py',HELPER)])
    c=get_call(r,call)
    target=next((f for f in r.flows if f.id==c.callee_id),None)
    assert target is not None
    assert target.path=='pkg/logic.py' and target.label=='save'
    assert c.resolution=='static-candidate'
    assert c.resolution_basis=='python-import'
    assert c.resolution_reason


@pytest.mark.parametrize('body', [
    '    from third_party import save\n    value = save(1)\n    return value\n',
    '    for save in callbacks:\n        value = save(1)\n    return value\n',
    '    with manager() as save:\n        value = save(1)\n    return value\n',
    '    value = [save(1) for save in callbacks]\n    return value\n',
    '    global save\n    value = save(1)\n    return value\n',
])
def test_shadowed_or_dynamic_python_names_never_jump_to_unrelated_function(body):
    text=HEADER+HELPER+"\n@app.get('/item')\ndef item():\n"+body
    r,_=analyze([('app/main.py',text)])
    c=get_call(r,'save')
    assert not c.callee_id
    assert c.resolution=='unresolved'
    assert c.resolution_reason


def test_nearest_enclosing_function_wins_not_global_name_match():
    text=HEADER+HELPER+"""
@app.get('/item')
def item():
    def save(value):
        return value + 1
    answer = save(1)
    return answer
"""
    r,_=analyze([('app/main.py',text)])
    c=get_call(r,'save')
    target=next((f for f in r.flows if f.id==c.callee_id),None)
    assert target is not None and target.line==8
    assert c.resolution_basis=='python-local'


@pytest.mark.parametrize('rebind', ['save = callback','def save(value):\n    return value * 2'])
def test_multiple_module_bindings_remain_unresolved(rebind):
    text=HEADER+"from .logic import save\n"+rebind+"\n@app.get('/x')\ndef x():\n    value=save(1)\n    return value\n"
    r,_=analyze([('app/main.py',text),('app/logic.py',HELPER)])
    assert not get_call(r,'save').callee_id


def test_same_line_http_and_reassigned_dictionary_have_distinct_provenance():
    text=HEADER+"import httpx\n@app.get('/x')\ndef x():\n    import httpx; v=httpx.get('https://real.test'); httpx={}; w=httpx.get('answer')\n    return v,w\n"
    r,_=analyze([('app/main.py',text)])
    steps=[s for f in r.flows if f.kind=='route' for s in f.steps if any(c.name=='httpx.get' for c in s.calls)]
    assert [s.category for s in steps]==['network','unknown']


def test_quality_distinguishes_read_from_parse_failure_and_lexical():
    r,_=analyze([('main.py',HEADER+"@app.get('/x')\ndef x():\n    return missing()\n"),
        ('broken.py','def invalid(:\n'),('client.js','const x=1;'),('package.json','{}')])
    q=r.analysis_quality
    assert q.source_files==3 and q.ast_files==1 and q.lexical_files==1 and q.parse_failed_files==1
    assert q.manifest_files==1 and q.unresolved_calls>0 and q.runtime_verified is False
    assert r.coverage.partial is False  # all selected files READ, not all parsed
    assert any(d.path=='broken.py' and d.code=='parse-error' for d in r.diagnostics)
    assert 'parse-error' in r.model_dump_json()


def test_uppercase_supported_python_extension_is_actually_parsed():
    r,_=analyze([('MAIN.PY',HEADER+"@app.get('/x')\ndef x(): return 1\n")])
    assert r.features and r.flows
    assert r.analysis_quality.ast_files==1


def test_verifier_rejects_false_call_resolution_and_quality_counts():
    r,snap=analyze([('main.py',HEADER+"@app.get('/x')\ndef x(): return missing()\n")])
    c=get_call(r,'missing');c.resolution='static-candidate'
    with pytest.raises(VerificationError):verify_analysis(r,snap)
    c.resolution='unresolved'
    r.analysis_quality.unresolved_calls=0
    with pytest.raises(VerificationError):verify_analysis(r,snap)


def remote_snapshot(items, *, invalid_size_path='', malformed_path=''):
    calls=[]; indexed={f'{i+1:040x}':(p,c) for i,(p,c) in enumerate(items)}
    def handler(req):
        path=req.url.path
        if '/git/blobs/' in path:
            ident=path.rsplit('/',1)[1];p,c=indexed[ident];calls.append(p)
            content='@@@' if p==malformed_path else base64.b64encode(c.encode()).decode()
            return httpx.Response(200,json={'encoding':'base64','content':content})
        if '/commits/' in path:return httpx.Response(200,json={'sha':'a'*40,'commit':{'tree':{'sha':'b'*40}}})
        if '/git/trees/' in path:
            return httpx.Response(200,json={'tree':[{'path':p,'type':'blob','mode':'100644','sha':sha,'size':len(c.encode())+(1 if p==invalid_size_path else 0)} for sha,(p,c) in indexed.items()],'truncated':False})
        return httpx.Response(200,json={'private':False,'default_branch':'main'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await GitHubReader(client).read('https://github.com/example/repo')
    return asyncio.run(run()),calls


def zipped(items):
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w') as z:
        for p,c in items:z.writestr('repo/'+p,c)
    return from_zip_bytes(raw.getvalue())


def test_github_uses_same_plan_and_reason_counts_as_zip_and_folder():
    items=[(f'src/help{i:03}.py','x=1\n') for i in range(160)]+[('app/main.py',HEADER),('.env','FAKE_SECRET'),('tests/test_x.py','x=1'),('README.md','doc')]
    g,calls=remote_snapshot(items);z=zipped(items);f=from_files([SourceFile(path=p,content=c) for p,c in items])
    assert 'app/main.py' in calls and len(calls)==160
    assert [x.path for x in g.files]==[x.path for x in z.files]==[x.path for x in f.files]
    for key in ('discovered','eligible','analyzed','skipped','omitted','failed','bytes_read','partial','reason_counts'):
        assert getattr(g.coverage,key)==getattr(z.coverage,key)==getattr(f.coverage,key),key


def test_github_applies_total_budget_before_downloading_blobs():
    content='#'+('x'*(MAX_FILE_BYTES-2))+'\n'
    items=[(f'src/a{i:02}.py',content) for i in range(40)]
    g,calls=remote_snapshot(items);z=zipped(items)
    assert len(calls)==32
    assert len(g.files)==len(z.files)==32
    assert g.coverage.bytes_read<=MAX_TOTAL_BYTES
    assert g.coverage.reason_counts==z.coverage.reason_counts=={'total_bytes':8}


@pytest.mark.parametrize('option', ['invalid_size_path','malformed_path'])
def test_bad_github_blob_is_reported_not_silent_complete(option):
    items=[('main.py',HEADER),('bad.py','x=1\n')]
    r,calls=remote_snapshot(items,**{option:'bad.py'})
    assert r.coverage.failed==1 and r.coverage.partial
    assert r.coverage.reason_counts.get('read_error')==1
    assert [f.path for f in r.files]==['main.py']


@pytest.mark.parametrize('wrapper', ['.hidden', '.venv', 'tests', 'node_modules', 'credentials'])
def test_excluded_wrapper_is_not_stripped_into_readable_source(wrapper):
    from app.intake import plan_files
    from app.models import FileMetadata
    selected, cov=plan_files([FileMetadata(path=f'{wrapper}/main.py',size=10)],strip_root=True)
    assert selected==[]
    assert cov.skipped==1


def test_diagnostics_ui_is_escaped_and_old_snapshots_are_readable():
    import json, subprocess
    from pathlib import Path
    js=Path('static/app.js').read_text()
    start=js.index('function analysisQualityDetails(')
    end=js.index('\nfunction ',start+1)
    code="""
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
"""+js[start:end]+"""
const actual=analysisQualityDetails({analysis_quality:{source_files:3,ast_files:1,lexical_files:1,parse_failed_files:1,calls:2,static_candidate_calls:1,unresolved_calls:1,unknown_steps:1},diagnostics:[{code:'parse-error',path:'<img>.py',message:'<bad>'}]});
console.log(JSON.stringify({actual,old:analysisQualityDetails({})}));
"""
    result=json.loads(subprocess.check_output(['node','-e',code],text=True))
    assert '<img>' not in result['actual'] and '&lt;img&gt;.py' in result['actual']
    assert '실제 실행 미검증' in result['actual']
    assert '진단 통계 없음' in result['old']


def test_import_binding_reexport_is_not_invented_as_a_definition():
    r,_=analyze([('app/main.py',HEADER+"from .proxy import save\n@app.get('/x')\ndef x(): return save(1)\n"),
                ('app/proxy.py','from .logic import save\n'),('app/logic.py',HELPER)])
    assert get_call(r,'save').resolution=='unresolved'
    assert '재수출' in get_call(r,'save').resolution_reason


def test_recursive_local_call_is_candidate_but_not_runtime_verified():
    text=HEADER+"def walk(n):\n    return walk(n-1)\n@app.get('/x')\ndef x(): return walk(2)\n"
    r,_=analyze([('main.py',text)])
    target=next(f for f in r.flows if f.label=='walk')
    assert target.steps[0].calls[0].callee_id==target.id
    assert r.analysis_quality.runtime_verified is False


def test_comprehension_later_iterable_uses_inner_target_not_outer_function():
    text=HEADER+HELPER+"\n@app.get('/x')\ndef x():\n    answer = [item for save in callbacks for item in save(1)]\n    return answer\n"
    r,_=analyze([('main.py',text)])
    assert not get_call(r,'save').callee_id


def test_comprehension_assignment_expression_invalidates_containing_binding():
    text=HEADER+HELPER+"\n@app.get('/x')\ndef x():\n    answer = [(save := callback) for callback in callbacks]\n    value = save(1)\n    return value\n"
    r,_=analyze([('main.py',text)])
    assert not get_call(r,'save').callee_id


def test_comprehension_first_iterable_can_use_outer_function():
    text=HEADER+HELPER+"\n@app.get('/x')\ndef x():\n    answer = [item for item in save(1)]\n    return answer\n"
    r,_=analyze([('main.py',text)])
    assert get_call(r,'save').resolution_basis=='python-local'


@pytest.mark.parametrize('imp,call', [('import pkg.logic','pkg.other.save'), ('import pkg','pkg.logic.save')])
def test_unimported_child_module_does_not_become_provenance(imp,call):
    text=HEADER+imp+"\n@app.get('/x')\ndef x():\n    value="+call+"(1)\n    return value\n"
    r,_=analyze([('pkg/main.py',text),('pkg/logic.py',HELPER),('pkg/other.py',HELPER)])
    assert not get_call(r,call).callee_id
