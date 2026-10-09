"""Fresh localhost HTTP acceptance. FlowLens runs; analyzed source never runs."""
from __future__ import annotations
import argparse, io, json, socket, subprocess, sys, time, zipfile
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='evidence/uml-http');args=p.parse_args()
    out=(ROOT/args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    text="""from fastapi import FastAPI
app=FastAPI()
@app.get('/guard')
def guard(data=None):
    if data is None:
        raise ValueError('missing')
    answer = cache.get('answer')
    return answer
"""
    items=[(f'repo/src/helper{i:03}.py','x=1\n') for i in range(160)]+[
        ('repo/app/main.py',text),('repo/.env','NOT_A_REAL_SECRET'),('repo/tests/test_x.py','x=1\n')]
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
        for path,content in items:z.writestr(path,content)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    log=(out/'server.log').open('w');server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=40) as client:
            for _ in range(60):
                try:
                    if client.get('/api/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            else:raise RuntimeError('server not ready')
            manifest=[{'path':p,'size':len(c.encode())} for p,c in items]
            plan=client.post('/api/file-plan',json={'entries':manifest});plan.raise_for_status()
            selected=plan.json()['selected']
            assert any(i['path']=='app/main.py' for i in selected)
            folder=client.post('/api/analyze',json={'source':'files','manifest':manifest,'files':[{'path':i['path'],'content':items[i['index']][1]} for i in selected]})
            folder.raise_for_status();a=folder.json()
            archive=client.post('/api/analyze-zip?filename=uml.zip',content=payload.getvalue(),headers={'Content-Type':'application/zip'})
            archive.raise_for_status();b=archive.json()
            for key in ['revision','nodes','edges','system_nodes','system_edges','features','flows','evidence','facts','analysis_quality','diagnostics']:assert a[key]==b[key],key
            assert a['coverage']['analyzed']==160 and a['coverage']['reason_counts']==b['coverage']['reason_counts']
            f=next(f for f in a['flows'] if f['kind']=='route');assert f['activity']['status']=='supported-subset'
            assert any(n['kind']=='decision' for n in f['activity']['nodes'])
            assert not any(s['category']=='network' for s in f['steps'])
            assert not f['activity']['runtime_verified']
            report={'ok':True,'transport':'actual localhost HTTP; not browser','version':a['analyzer_version'],'checks':['161st entrypoint selected','folder/ZIP same analysis including UML','160-file and secret exclusion unchanged','if/raise branches retained','dict.get not network','runtime not verified'],'coverage':a['coverage']}
            for name,data in [('folder.json',a),('zip.json',b),('report.json',report)]: (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
            print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:
        server.terminate()
        try:server.wait(timeout=8)
        except subprocess.TimeoutExpired:server.kill();server.wait()
        log.close()
if __name__=='__main__':main()
