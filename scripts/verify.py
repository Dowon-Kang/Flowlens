"""Bounded verification: unit -> skills -> HTTP/ZIP -> optional browser/live.

Executes FlowLens tests only, never code from the analyzed repository.
Records real commands, failures and logs, and terminates its own HTTP server.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import zipfile
import httpx

ROOT=Path(__file__).resolve().parents[1]


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='evidence/latest')
    parser.add_argument('--browser',action='store_true')
    parser.add_argument('--bridge',action='store_true',help='Explicit in-process browser fallback, not HTTP browser success')
    parser.add_argument('--executable',default=os.getenv('PLAYWRIGHT_CHROMIUM_EXECUTABLE'))
    parser.add_argument('--live',metavar='GITHUB_URL')
    args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    checks=[]

    def command(name,cmd,timeout=180):
        start=time.monotonic()
        try:
            run=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
            code,log=run.returncode,run.stdout+run.stderr
        except (subprocess.TimeoutExpired,OSError) as exc:
            code,log=124,str(exc)
        (out/f'{name}.log').write_text(log,encoding='utf-8')
        checks.append({'name':name,'command':cmd,'exit_code':code,'seconds':round(time.monotonic()-start,3),'log':f'{name}.log'})
        print(f'{name}: {"PASS" if code==0 else "FAIL"}',flush=True)

    command('unit',[sys.executable,'-m','pytest','-q'])
    command('skills',[sys.executable,'scripts/check_skills.py'])
    command('javascript',['node','--check','static/app.js'])
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    with (out/'server.log').open('w',encoding='utf-8') as server_log:
        server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,stdout=server_log,stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url=base,timeout=145,trust_env=False) as client:
                ready=False
                for _ in range(60):
                    try:
                        response=client.get('/api/health')
                        if response.status_code==200:ready=True;break
                    except httpx.HTTPError:pass
                    if server.poll() is not None:break
                    time.sleep(.2)
                if not ready:raise RuntimeError('HTTP server did not become ready')
                health=response.json()
                assert client.get('/').status_code==200
                assert client.get('/static/app.js').status_code==200
                data=io.BytesIO()
                with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
                    for path in sorted((ROOT/'app').glob('*.py')):z.write(path,'flowlens/app/'+path.name)
                    z.writestr('flowlens/README.md','# excluded')
                response=client.post('/api/analyze-zip?filename=flowlens-self.zip',content=data.getvalue(),headers={'Content-Type':'application/zip'})
                assert response.status_code==200,response.text
                result=response.json()
                assert result['source']=='zip' and result['analyzer_version']==health['version']
                assert result['features'] and result['evidence'] and result['coverage']['failed']==0
                assert len(result['system_nodes'])<=8
                (out/'self-zip.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
                bad=io.BytesIO()
                with zipfile.ZipFile(bad,'w') as z:z.writestr('../escape.py','x=1')
                assert client.post('/api/analyze-zip',content=bad.getvalue(),headers={'Content-Type':'application/zip'}).status_code==400
                assert client.post('/api/analyze',json={'source':'github','url':'http://127.0.0.1/private'}).status_code==400
                checks.append({'name':'http-zip','exit_code':0,'version':health['version'],'coverage':result['coverage'],'features':[f['label'] for f in result['features']]})
                print('http-zip: PASS',flush=True)
            if args.browser:
                cmd=[sys.executable,'scripts/browser_smoke.py','--url',base,'--output',str(out/'browser')]
                if args.bridge:cmd.append('--bridge')
                if args.executable:cmd+=['--executable',args.executable]
                command('browser-bridge' if args.bridge else 'browser-http',cmd)
            if args.live:
                command('live-github-zip',[sys.executable,'scripts/live_github_check.py',args.live,'--base-url',base,'--zip','--output',str(out/'live.json')],360)
        except Exception as exc:
            checks.append({'name':'http-cycle','exit_code':1,'error':str(exc)})
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()
    ok=all(c['exit_code']==0 for c in checks)
    report={'ok':ok,'at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version.split()[0],'browser_transport':'in-process bridge' if args.bridge else 'HTTP' if args.browser else 'not run','live_requested':bool(args.live),'checks':checks}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Execution verification','',f'Overall: {"PASS" if ok else "FAIL / see checks"}','','| Check | Result |','|---|---|']
    lines += [f'| {c["name"]} | {"PASS" if c["exit_code"]==0 else "FAIL"} |' for c in checks]
    lines += ['','Actual commands and logs are in report.json. A bridge pass is not an HTTP browser pass. An unrun live check is not a GitHub success. No target code or paid AI was executed.']
    (out/'EXECUTION_VALIDATION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
