import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from app.intake import from_zip_bytes, IntakeError
from app.main import app

client = TestClient(app)

def make_zip(entries: dict[str, bytes | str]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path, content in entries.items():
            if isinstance(content, str):
                content = content.encode('utf-8')
            zf.writestr(path, content)
    return stream.getvalue()

def test_zip_strips_github_wrapper_and_analyzes_sources():
    raw = make_zip({
        'sample-main/backend/main.py': "from fastapi import FastAPI\napp=FastAPI()\n@app.get('/health')\ndef health(): return {'ok': True}\n",
        'sample-main/README.md': '# ignored',
    })
    snapshot = from_zip_bytes(raw, 'sample-main.zip')
    assert snapshot.source == 'zip'
    assert snapshot.files[0].path == 'backend/main.py'
    assert snapshot.coverage.discovered == 2
    assert any('디스크에 풀거나' in note for note in snapshot.coverage.notes)

def test_zip_api_end_to_end():
    raw = make_zip({
        'project/src/server.ts': "import { Hono } from 'hono';\nconst app=new Hono();\napp.get('/users', c => c.json([]));\n",
        'project/src/client.ts': "fetch('/users', { method: 'GET' });\n",
    })
    r = client.post('/api/analyze-zip?filename=project.zip', content=raw, headers={'content-type':'application/zip'})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['source'] == 'zip'
    assert body['name'] == 'project'
    assert len(body['features']) == 1
    assert [stage['name'] for stage in body['stages']] == ['INTAKE','EXTRACT','BUILD','VERIFY','EXPLAIN']

def test_zip_path_traversal_rejected():
    raw = make_zip({'../escape.py': 'x=1'})
    with pytest.raises(IntakeError):
        from_zip_bytes(raw)

def test_non_zip_rejected():
    with pytest.raises(IntakeError):
        from_zip_bytes(b'not a zip')

def test_zip_binary_source_is_not_analyzed():
    raw = make_zip({'project/main.py': b'\x00\x01\x02'})
    with pytest.raises(IntakeError):
        from_zip_bytes(raw)
