"""Identical metadata policy across directory browser intake and ZIP, including index 161."""
import json
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import SourceFile
from app.intake import from_files, from_zip_bytes, MAX_FILE_BYTES, MAX_TOTAL_BYTES
from tests.test_zip import make_zip

ROOT=Path(__file__).resolve().parents[1]
client=TestClient(app)
ENTRY="from fastapi import FastAPI\napp=FastAPI()\n@app.get('/health')\ndef health(): return {'ok': True}\n"


def fixture():
    items=[(f'repo/src/helper{i:03}.py','x=1\n') for i in range(160)]
    items.append(('repo/app/main.py',ENTRY))  # 161st, not within raw[:160]
    items.extend([('repo/.env','FAKE_SECRET'),('repo/README.md','# ignored'),
                  ('repo/migrations/convert.py','x=2'),('repo/app/model.freezed.dart','void x() {}'),
                  ('repo/tests/main.py','x=2'),('repo/credential.py','FAKE_SECRET'),
                  ('repo/upper.PY','x=3')])
    return items


def manifest(items):
    return [{'path':p,'size':len(c.encode('utf8'))} for p,c in items]


def browser(items):
    res=client.post('/api/file-plan',json={'entries':manifest(items)})
    plan=res.json() if res.status_code==200 else None
    run=subprocess.run(['node','tests/folder_handler.cjs'],cwd=ROOT,input=json.dumps({'files':[{'path':p,'content':c} for p,c in items],'plan':plan}),text=True,capture_output=True,check=True)
    return json.loads(run.stdout)


def test_browser_keeps_the_161st_entrypoint_and_matches_zip():
    items=fixture();output=browser(items)
    assert output['payload'],output
    names={f['path'] for f in output['payload']['files']}
    assert 'app/main.py' in names
    zip_snapshot=from_zip_bytes(make_zip(dict(items)))
    assert names=={f.path for f in zip_snapshot.files}
    assert all(not any(x in p for x in ('.env','credential','migrations/','.freezed.','tests/')) for p in output['read'])


def test_browser_manifest_and_reasons_survive_api_json():
    items=fixture();output=browser(items)
    response=client.post('/api/analyze',json=output['payload'])
    assert response.status_code==200,response.text
    cov=response.json()['coverage']
    assert cov['discovered']==len(items)
    expected=from_zip_bytes(make_zip(dict(items))).coverage
    for key in ('discovered','eligible','analyzed','skipped','omitted','failed','bytes_read','partial','reason_counts'):
        assert cov[key]==getattr(expected,key),key
    assert cov['browser_selection']['reported_by']=='browser'
    assert cov['browser_selection']['transmitted']==160
    assert cov['browser_selection']['reason_counts']==cov['reason_counts']
    assert cov['skipped']+cov['omitted']==len(items)-160
    assert 'FAKE_SECRET' not in response.text


def test_folder_policy_is_server_owned_metadata_only():
    output=browser(fixture())
    assert len(output['requests'])==1
    req=output['requests'][0]
    assert req['url']=='/api/file-plan'
    assert len(req['body']['entries'])==len(fixture())
    assert all(set(i)=={'path','size'} for i in req['body']['entries'])


def test_policy_endpoint_preserves_limits_and_rejects_invalid_paths():
    response=client.post('/api/file-plan',json={'entries':[{'path':'repo/main.py','size':32},{'path':'repo/big.py','size':MAX_FILE_BYTES+1}]})
    assert response.status_code==200,response.text
    assert [p['path'] for p in response.json()['selected']]==['main.py']
    assert response.json()['coverage']['omitted']==1
    assert client.post('/api/file-plan',json={'entries':[{'path':'../main.py','size':3}]}).status_code==400
    assert client.post('/api/file-plan',json={'entries':[{'path':'a.py','size':-1}]}).status_code==422
    assert client.post('/api/file-plan',json={'entries':[{'path':'a.py','size':'3'}]}).status_code==422


def test_direct_files_and_zip_same_failed_binary_accounting():
    entries=[('main.py',ENTRY),('nul.py','x="\x00"')]
    folder=from_files([SourceFile(path=p,content=c) for p,c in entries])
    z=from_zip_bytes(make_zip(dict(entries)))
    assert folder.coverage.failed==z.coverage.failed==1
    assert folder.coverage.omitted==z.coverage.omitted==0


def test_metadata_cannot_hide_or_add_transmitted_files():
    data={'source':'files','manifest':[{'path':'repo/main.py','size':len(ENTRY.encode())}],
          'files':[{'path':'main.py','content':ENTRY}],'read_failures':[]}
    r=client.post('/api/analyze',json=data)
    assert r.status_code==200,r.text
    data['files'].append({'path':'extra.py','content':'x=1'})
    assert client.post('/api/analyze',json=data).status_code==400
    data['files']=[]
    assert client.post('/api/analyze',json=data).status_code==400


def test_file_count_byte_budget_and_secrets_not_relaxed():
    content='#'+('x'*(MAX_FILE_BYTES-2))+'\n'
    items=[(f'repo/s{i:02}.py',content) for i in range(40)]+[('repo/.env','SECRET')]
    output=browser(items)
    response=client.post('/api/analyze',json=output['payload'])
    assert response.status_code==200,response.text
    cov=response.json()['coverage'];z=from_zip_bytes(make_zip(dict(items))).coverage
    assert cov['bytes_read']<=MAX_TOTAL_BYTES
    assert cov['analyzed']==z.analyzed==32
    assert cov['omitted']==z.omitted==8
    assert cov['skipped']==z.skipped==1


def test_browser_bom_and_unicode_bytes_match_zip():
    items=[('repo/main.py','\ufeff'+ENTRY),('repo/message.py',"value='한글 😀'\n")]
    output=browser(items)
    response=client.post('/api/analyze',json=output['payload'])
    assert response.status_code==200,response.text
    z=from_zip_bytes(make_zip(dict(items)))
    assert response.json()['revision']==z.revision
    assert response.json()['coverage']['bytes_read']==z.coverage.bytes_read


def test_unknown_missing_or_size_mismatch_is_not_complete_success():
    metadata=[{'path':'repo/main.py','size':len(ENTRY.encode())}]
    base={'source':'files','manifest':metadata,'files':[{'path':'main.py','content':ENTRY}]}
    bad={**base,'manifest':[{'path':'repo/main.py','size':1}]}
    assert client.post('/api/analyze',json=bad).status_code==400
    bad={**base,'read_failures':[{'path':'not-selected.py','reason':'read_error'}]}
    assert client.post('/api/analyze',json=bad).status_code==400


def test_read_failure_budget_is_shared_no_backfill(monkeypatch):
    import app.intake as intake
    monkeypatch.setattr(intake,'MAX_FILES',2)
    entries=[('repo/main.py',ENTRY),('repo/a.py','\x00'),('repo/z.py','x=1')]
    output=browser(entries)
    response=client.post('/api/analyze',json=output['payload'])
    assert response.status_code==200,response.text
    cov=response.json()['coverage'];zip_cov=from_zip_bytes(make_zip(dict(entries))).coverage
    assert cov['failed']==zip_cov.failed==1
    assert cov['omitted']==zip_cov.omitted==1
    assert cov['reason_counts']==zip_cov.reason_counts
    assert len(output['read'])==2
