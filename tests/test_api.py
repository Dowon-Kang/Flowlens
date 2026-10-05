from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health_has_no_secrets():
    r=client.get('/api/health')
    assert r.status_code==200 and 'OPENAI_API_KEY' not in r.text

def test_demo_end_to_end():
    r=client.post('/api/analyze',json={'source':'demo'})
    assert r.status_code==200
    j=r.json()
    assert [s['name'] for s in j['stages']]==['INTAKE','EXTRACT','BUILD','VERIFY','EXPLAIN']
    assert j['stages'][-1]['status']=='skipped'
    assert j['explanation'] is None
    assert len(j['features'])==3

def test_local_source_end_to_end():
    r=client.post('/api/analyze',json={'source':'files','files':[{'path':'main.py','content':"from fastapi import FastAPI\napp=FastAPI()\n@app.get('/health')\ndef health():\n    return {'ok':True}\n"}]})
    assert r.status_code==200 and len(r.json()['features'])==1

def test_invalid_url():
    r=client.post('/api/analyze',json={'source':'github','url':'http://localhost/private'})
    assert r.status_code==400

def test_cross_origin_rejected():
    r=client.post('/api/analyze',json={'source':'demo'},headers={'origin':'https://evil.test'})
    assert r.status_code==403

def test_ai_missing_config_falls_back(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('OPENAI_MODEL',raising=False)
    r=client.post('/api/analyze',json={'source':'demo','explain':True})
    assert r.status_code==200 and r.json()['explanation'] is None
    assert any('OPENAI' in w for w in r.json()['warnings'])

def test_invalid_body_not_echoed():
    r=client.post('/api/analyze',json={'source':'secret-input'})
    assert r.status_code==422 and 'secret-input' not in r.text

def test_host_header_guard():
    from fastapi.testclient import TestClient
    from app.main import app
    response=TestClient(app).get('/api/health',headers={'host':'attacker.invalid'})
    assert response.status_code==400
