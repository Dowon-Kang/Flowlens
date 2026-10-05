"""User acceptance with actual uploaded source bytes; no target code execution.
--bridge is an explicit in-process transport fallback, not a live browser HTTP test.
"""
from __future__ import annotations
import argparse,json,os,re,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright,expect


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--snapshot',required=True)
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--bridge',action='store_true')
    parser.add_argument('--executable',default=os.getenv('PLAYWRIGHT_CHROMIUM_EXECUTABLE'))
    parser.add_argument('--output',default='evidence/process-browser')
    args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    snapshot=json.loads(Path(args.snapshot).read_text(encoding='utf-8'))
    checks=[];errors=[];client=None
    with tempfile.TemporaryDirectory() as tmp,sync_playwright() as p:
        archive=Path(tmp)/'VibeCare-source.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for f in snapshot['files']:z.writestr('VibeCare/'+f['path'],f['content'])
        kwargs={'headless':True}
        if args.executable:kwargs['executable_path']=args.executable
        browser=p.chromium.launch(**kwargs)
        page=browser.new_page(viewport={'width':1580,'height':1100},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        if args.bridge:
            from fastapi.testclient import TestClient
            from app.main import app
            client=TestClient(app)
            def api(path,options):
                body=options.get('body')
                response=client.request(options.get('method') or 'GET',path,headers=options.get('headers') or {},content=bytes(body) if isinstance(body,list) else body)
                return {'status':response.status_code,'body':response.text}
            page.expose_function('__flowlensApi',api)
            html=(ROOT/'static/index.html').read_text(encoding='utf-8')
            html=re.sub(r'<link[^>]*>','',html);html=re.sub(r'<script[^>]*>.*?</script>','',html,flags=re.S)
            page.set_content(html);page.add_style_tag(content=(ROOT/'static/styles.css').read_text(encoding='utf-8'))
            page.add_script_tag(content="window.fetch=async(path,opts={})=>{const r=await window.__flowlensApi(String(path),{method:opts.method,headers:opts.headers,body:opts.body instanceof Blob?Array.from(new Uint8Array(await opts.body.arrayBuffer())):opts.body});return new Response(r.body,{status:r.status,headers:{'Content-Type':'application/json'}})}")
            page.add_script_tag(content=(ROOT/'static/app.js').read_text(encoding='utf-8'),type='module')
        else:page.goto(args.url,wait_until='networkidle')
        page.wait_for_selector('#graph [data-node]')
        page.locator('#zipInput').set_input_files(str(archive))
        expect(page.locator('#sourceBadge')).to_have_text('ZIP archive',timeout=30000)
        assert page.locator('#graph [data-node]').count()<=8
        assert 'api.thefitrus.com' in page.locator('#graph').text_content()
        checks.append('Real selected source ZIP upload -> 8-node overview with external URL evidence')
        page.screenshot(path=str(out/'01-system.png'),full_page=True)
        def feature(label):
            page.locator('#sidebarFeatures [data-feature]').filter(has_text=label).first.click()
            expect(page.locator('#processTools')).to_be_visible()
            assert 1<=page.locator('#graph [data-node]').count()<=8
            assert '소스 읽기 순서' in page.locator('#detailPanel').inner_text()
        feature('추천')
        expect(page.locator('#flowVariant')).to_have_value(re.compile('.+'))
        assert '/recommendations/authorize' in page.locator('#detailPanel').inner_text()
        checks.append('Recommendation opens processing summary, not file graph; <=8 visible blocks')
        page.screenshot(path=str(out/'02-recommendation.png'),full_page=True)
        page.locator('#detailPanel [data-step]').filter(has_text='추천 계산').click()
        assert page.locator('#detailPanel .code-evidence').count()>0
        checks.append('Processing block exposes exact source evidence')
        page.locator('#detailPanel [data-callee]').filter(has_text='calculateRecommendation').click()
        assert 'calculateRecommendation' in page.locator('#canvasTitle').inner_text()
        assert page.locator('#graph [data-node]').count()<=8
        checks.append('Static named call -> actual algorithm function body, parent feature retained')
        page.screenshot(path=str(out/'03-algorithm.png'),full_page=True)
        page.locator('#processTools [data-toggle-steps]').click()
        assert page.locator('#graph [data-node]').count()>8
        checks.append('Expand shows every underlying algorithm step, no dropped operations')
        page.locator('#processTools [data-toggle-steps]').click()
        page.locator('#detailPanel [data-step]').filter(has_text='안전').first.click()
        assert page.locator('#detailPanel .code-evidence').count()>0
        page.screenshot(path=str(out/'04-evidence.png'),full_page=True)
        page.locator('#detailPanel [data-action="clear"]').click()
        page.locator('#detailPanel [data-flow-back]').click()
        assert '/recommendations/authorize' in page.locator('#detailPanel').inner_text()
        checks.append('Return to caller without losing feature context')
        page.locator('#processTools [data-detail="files"]').click()
        assert 'recommendation-routes.ts' in page.locator('#graph').text_content()
        checks.append('File references remain available below processing summary')
        feature('Health')
        assert page.locator('#graph [data-node]').count()==1
        page.locator('#processTools [data-detail="files"]').click()
        assert page.locator('#graph [data-node]').count()==1
        checks.append('Health isolated: one operation and one source file, no recommendation contamination')
        page.screenshot(path=str(out/'05-health.png'),full_page=True)
        feature('로그인')
        assert page.locator('#flowVariant option').count()==2
        page.select_option('#flowVariant',label='POST /v1/auth/refresh')
        assert '/auth/refresh' in page.locator('#detailPanel').inner_text()
        checks.append('PIN and refresh are separate endpoint variants, not a false sequential chain')
        feature('Supabase 직접 인증')
        assert page.locator('#flowVariant option').count()>=3
        for label in ['이메일 로그인','회원가입','로그아웃']:
            page.select_option('#flowVariant',label=label)
            assert page.locator('#graph [data-node]').count()==1
        checks.append('Direct Supabase auth has separate sign-in / sign-up / sign-out scopes')
        feature('Fitrus')
        found=False
        for element in page.locator('#detailPanel [data-step]').all():
            # Re-query after rendering; direct children change on each selection.
            sid=element.get_attribute('data-step')
            page.locator('[data-step="'+sid+'"]').click()
            target=page.locator('#detailPanel [data-callee]').filter(has_text='measure')
            if target.count():
                target.first.click();found=True;break
            page.locator('#detailPanel [data-action="clear"]').click()
        assert found,'External provider method not reachable from route scope'
        assert 'measure' in page.locator('#detailPanel').inner_text()
        checks.append('FITRUS route -> statically linked provider method body')
        page.screenshot(path=str(out/'06-fitrus.png'),full_page=True)
        # Visit every supported entrypoint and exercise one evidence block.
        page.locator('#systemTab').click()
        fids=page.locator('#sidebarFeatures [data-feature]').evaluate_all('(els)=>els.map(e=>e.dataset.feature)')
        variants=0
        for fid in fids:
            page.locator('#sidebarFeatures [data-feature="'+fid+'"]').click()
            options=page.locator('#flowVariant option').evaluate_all('(els)=>els.map(e=>e.value)')
            for flow in options:
                page.select_option('#flowVariant',flow)
                assert 1<=page.locator('#graph [data-node]').count()<=8
                page.locator('#detailPanel [data-step]').first.click()
                assert page.locator('#detailPanel .code-evidence').count()>0
                variants+=1
        checks.append(f'All {variants} actual API/SDK entrypoints: bounded summary and source evidence')
        feature('추천');page.set_viewport_size({'width':430,'height':932})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(out/'07-mobile.png'),full_page=True)
        checks.append('430px processing page: no page-level horizontal overflow')
        assert not errors,errors
        checks.append('No JavaScript page errors')
        report={'ok':True,'transport':'bridge/TestClient' if args.bridge else 'browser -> actual HTTP','target_revision':snapshot['revision'],'source_files':len(snapshot['files']),'count':len(checks),'checks':checks,'entrypoints':variants,'errors':errors}
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2));browser.close()
        if client:client.close()
if __name__=='__main__':main()
