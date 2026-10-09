"""UI smoke checks. --bridge uses a real FastAPI TestClient, NOT live HTTP.
Default mode uses a running localhost server. No browser policy is modified.
"""
from __future__ import annotations
import argparse, json, os, re, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright, expect


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bridge',action='store_true',help='Test in-memory HTML -> JS fetch bridge -> FastAPI TestClient')
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--output',default=str(ROOT/'evidence'))
    parser.add_argument('--executable',default=os.getenv('PLAYWRIGHT_CHROMIUM_EXECUTABLE'))
    args=parser.parse_args(); out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];client=None
    with sync_playwright() as p:
        kwargs={'headless':True}
        if args.executable:kwargs['executable_path']=args.executable
        browser=p.chromium.launch(**kwargs)
        page=browser.new_page(viewport={'width':1600,'height':1140},device_scale_factor=1)
        page.on('pageerror',lambda error:errors.append(str(error)))
        if args.bridge:
            from fastapi.testclient import TestClient
            from app.main import app
            client=TestClient(app)
            def api(path,options):
                response=client.request(options.get('method','GET'),path,headers=options.get('headers',{}),content=bytes(options['body']) if isinstance(options.get('body'),list) else options.get('body'))
                return {'status':response.status_code,'body':response.text}
            page.expose_function('__flowlensApi',api)
            html=(ROOT/'static/index.html').read_text(encoding='utf-8')
            html=re.sub(r'<link[^>]*>','',html)
            html=re.sub(r'<script[^>]*>.*?</script>','',html,flags=re.S)
            page.set_content(html)
            page.add_style_tag(content=(ROOT/'static/styles.css').read_text(encoding='utf-8'))
            page.add_script_tag(content="window.fetch=async(path,opts={})=>{const r=await window.__flowlensApi(String(path),{method:opts.method,headers:opts.headers,body:opts.body instanceof Blob?Array.from(new Uint8Array(await opts.body.arrayBuffer())):opts.body});return new Response(r.body,{status:r.status,headers:{'Content-Type':'application/json'}})}")
            page.add_script_tag(content=(ROOT/'static/app.js').read_text(encoding='utf-8'),type='module')
        else:
            page.goto(args.url,wait_until='networkidle')
        page.wait_for_selector('#graph [data-node]')
        assert page.locator('#graph [data-node]').count()==7
        assert page.locator('#detailPanel [data-feature]').count()==3
        checks.append('System overview: 7 nodes, 3 discoverable features')
        page.screenshot(path=str(out/'system-flow.png'),full_page=True)
        page.locator('#detailPanel [data-feature]').filter(has_text='측정 데이터').click()
        assert '측정 데이터' in page.locator('#canvasTitle').inner_text()
        assert page.locator('#featureContext').is_visible()
        assert 1 <= page.locator('#graph [data-node]').count() <= 8
        assert page.locator('#processTools').is_visible()
        page.locator('#processTools [data-detail="files"]').click()
        checks.append('Feature view: selected feature slice and parent context visible')
        page.screenshot(path=str(out/'feature-flow.png'),full_page=True)
        page.locator('#graph [data-node]').filter(has=page.locator('title',has_text='measurement-service.ts')).first.click()
        assert page.locator('#detailPanel .code-evidence').count()>0
        assert 'SOURCE EVIDENCE' in page.locator('#detailPanel').inner_text()
        checks.append('Code evidence: selected file, source lines and declared symbols')
        page.screenshot(path=str(out/'code-evidence.png'),full_page=True)
        page.locator('#systemTab').click()
        page.locator('#graph [data-edge]').first.click()
        assert 'CONNECTION EVIDENCE' in page.locator('#detailPanel').inner_text()
        checks.append('Edge evidence selection')
        page.locator('#zoomIn').click();assert page.locator('#zoomLabel').inner_text()=='120%'
        page.locator('#fitView').click();assert page.locator('#zoomLabel').inner_text()=='100%'
        checks.append('Zoom and fit controls')
        # Inspect generated Blob payloads without navigating or changing browser policy.
        page.evaluate("""() => {window.__exports=[]; URL.createObjectURL=(blob)=>{window.__exports.push(blob);return 'blob:test-export'};URL.revokeObjectURL=()=>{};const original=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){if(!this.download)original.call(this)}}""")
        for kind in ['json','svg','md']:
            page.locator('#exportButton').click();page.locator('[data-export="'+kind+'"]').click()
        exports=page.evaluate('Promise.all(window.__exports.map(b=>b.text()))')
        assert json.loads(exports[0])['schema_version']=='1.2'
        assert '<svg' in exports[1] and 'flowchart TD' in exports[2]
        checks.append('JSON, SVG and Markdown export payloads (not OS save dialog)')
        page.locator('#pipelineNav').click()
        assert page.locator('.pipeline-stage').count()==5
        assert '런타임' in page.locator('#pipelineView').inner_text() or '운영' in page.locator('#pipelineView').inner_text()
        checks.append('Actual stage history and analysis limitations visible')
        page.locator('[data-demo="python"]').click()
        expect(page.locator("#repoName")).to_contain_text("TaskBoard")
        assert 'FastAPI Backend' in page.locator('#graph').text_content()
        assert 'Flutter App' not in page.locator('#graph').text_content()
        checks.append('Different repository/stack changes overview')
        page.locator('#helpButton').click();assert page.locator('#helpDialog').is_visible();page.locator('#closeHelp').click()
        checks.append('Help dialog opens and closes')
        page.locator('#folderInput').set_input_files(str(ROOT/'fixtures/python-demo'))
        expect(page.locator("#sourceBadge")).to_have_text("Local files")
        assert 'FastAPI Backend' in page.locator('#graph').text_content()
        checks.append('Actual folder picker selection -> file contents -> API -> new graph')
        if True:  # Both modes test selected ZIP bytes.
            with tempfile.TemporaryDirectory() as td:
                zip_path=Path(td)/'zip-browser-demo.zip'
                with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr('zip-browser-demo/src/main.py', "from fastapi import FastAPI\napp=FastAPI()\n@app.get('/zip-health')\ndef health(): return {'ok': True}\n")
                page.locator('#zipInput').set_input_files(str(zip_path))
                expect(page.locator("#sourceBadge")).to_have_text("ZIP archive")
                assert 'FastAPI Backend' in page.locator('#graph').text_content()
                assert 'zip-browser-demo' in page.locator('#repoName').inner_text()
                checks.append('Actual ZIP picker -> raw ZIP upload -> safe server intake -> graph')
        # New UML user story: selected source bytes are DATA, never executed.
        with tempfile.TemporaryDirectory() as td:
            archive=Path(td)/'uml-browser-demo.zip'
            fixture=("from fastapi import FastAPI\napp=FastAPI()\n"
                "@app.get('/guard')\ndef guard(data=None):\n"
                "    if data is None:\n        raise ValueError('missing')\n"
                "    return {'ok': True}\n"
                "@app.get('/unsupported')\ndef unsupported():\n"
                "    for x in items:\n        save(x)\n    return None\n")
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('uml-browser-demo/backend/main.py',fixture)
            page.locator('#zipInput').set_input_files(str(archive))
            expect(page.locator('#repoName')).to_contain_text('uml-browser-demo')
            page.locator('#sidebarFeatures [data-feature]').filter(has_text='Guard').click()
            page.locator('#processTools [data-detail="activity"]').click()
            expect(page.locator('#canvasTitle')).to_contain_text('UML')
            assert page.locator('#graph polygon').count()==1
            assert '[true]' in page.locator('#graph').inner_text()
            assert '[false]' in page.locator('#graph').inner_text()
            page.locator('#graph [data-node]').filter(has=page.locator('title',has_text='raise ValueError')).first.click()
            assert page.locator('#detailPanel .code-evidence').count()>0
            assert '실행 미검증' in page.locator('#detailPanel').inner_text()
            page.screenshot(path=str(out/'uml-activity.png'),full_page=True)
            checks.append('UML activity: actual ZIP upload -> guarded branches -> exception evidence')
            page.locator('#sidebarFeatures [data-feature]').filter(has_text='Unsupported').click()
            page.locator('#processTools [data-detail="activity"]').click()
            expect(page.locator('#detailPanel')).to_contain_text('활동 흐름 미생성')
            assert page.locator('#graph [data-node]').count()==0
            page.locator('#detailPanel [data-detail="steps"]').click()
            assert page.locator('#graph [data-node]').count()>0
            checks.append('Unsupported UML grammar: explicit reason, empty graph, source-order fallback')
        page.locator('[data-demo="mobile"]').click()
        expect(page.locator("#repoName")).to_contain_text("FlowCare")
        page.set_viewport_size({'width':430,'height':932})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(out/'mobile-view.png'),full_page=True)
        checks.append('Mobile layout: no horizontal page overflow at 430px')
        assert not errors, errors
        checks.append('No JavaScript page errors')
        report={'mode':'browser-ui + in-process FastAPI bridge' if args.bridge else 'browser -> HTTP server','checks':checks,'count':len(checks),'errors':errors,'network_limit':'Live browser HTTP navigation not covered by bridge mode. No live GitHub/OpenAI request in this suite.'}
        (out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        browser.close()
        if client:client.close()

if __name__=='__main__':main()
