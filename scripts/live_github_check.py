"""Read-only live check: HTTP API -> real GitHub -> same-commit ZIP.
No target code execution, LLM calls, hidden retries or demo fallback.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote,urlparse
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.intake import parse_github_url,MAX_ZIP_BYTES


def summarize(result):
    return {'source':result['source'],'name':result['name'],'revision':result['revision'],'coverage':result['coverage'],'system_nodes':[n['label'] for n in result['system_nodes']],'features':[f['label'] for f in result['features']],'http_candidates':sum(e['relation']=='http-contract' for e in result['edges']),'warnings':result['warnings']}


def validate(result,owner,repo):
    assert result['nodes'] and result['evidence'],'No evidence graph'
    assert result['coverage']['analyzed']>0
    assert result['coverage']['failed']==0,'Selected source downloads failed'
    assert len(result['system_nodes'])<=8,'Overview exceeds eight nodes'
    if (owner+'/'+repo).lower()=='dowon-kang/vibecare-pilot':
        labels={n['label'] for n in result['system_nodes']}
        expected={'Flutter App','Riverpod / Controller','Service / Dio','Hono Backend','Supabase','PostgreSQL client'}
        assert expected<=labels,f'Missing layers: {sorted(expected-labels)}'
        endpoints=[x for f in result['features'] for x in f['endpoint_labels']]
        for domain in ('/auth/','/fitrus/','/recommendations/'):
            assert any(domain in label for label in endpoints),f'Missing feature: {domain}'
        assert any(e['relation']=='http-contract' for e in result['edges']),'No HTTP candidates'
        from acceptance_flow import validate_semantics
        validate_semantics(result)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('url',nargs='?',default='https://github.com/Dowon-Kang/vibecare-pilot')
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--zip',action='store_true')
    parser.add_argument('--output',default='evidence/live-github.json')
    args=parser.parse_args()
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    report={'ok':False,'url':args.url,'checks':[]}
    try:
        owner,repo=parse_github_url(args.url)
        local=urlparse(args.base_url)
        if local.scheme!='http' or local.hostname not in {'127.0.0.1','localhost'} or local.username or local.password:
            raise ValueError('Verification server must be localhost HTTP')
        with httpx.Client(base_url=args.base_url,timeout=150,trust_env=False,follow_redirects=False) as client:
            response=client.post('/api/analyze',json={'source':'github','url':args.url,'explain':False})
            if response.status_code!=200:raise RuntimeError(f'GitHub flow: HTTP {response.status_code}: {response.text[:600]}')
            result=response.json();validate(result,owner,repo)
            sha=result['revision']
            assert re.fullmatch(r'[a-fA-F0-9]{40}',sha),'Commit not pinned'
            assert all('/blob/'+sha+'/' in e['url'] for e in result['evidence'] if e['url'])
            (out.parent/'github-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            report['checks'].append(summarize(result))
            if args.zip:
                # No credentials are forwarded to codeload or redirects.
                archive_url=f'https://codeload.github.com/{quote(owner)}/{quote(repo)}/zip/{sha}'
                data=bytearray()
                with httpx.Client(timeout=60,trust_env=False,follow_redirects=False) as download:
                    with download.stream('GET',archive_url) as archive:
                        archive.raise_for_status()
                        for chunk in archive.iter_bytes():
                            data.extend(chunk)
                            if len(data)>MAX_ZIP_BYTES:raise ValueError('Live archive exceeds ZIP limit')
                response=client.post('/api/analyze-zip',params={'filename':repo+'.zip'},content=bytes(data),headers={'Content-Type':'application/zip'})
                if response.status_code!=200:raise RuntimeError(f'ZIP flow: HTTP {response.status_code}: {response.text[:600]}')
                zipped=response.json();validate(zipped,owner,repo)
                (out.parent/'zip-analysis.json').write_text(json.dumps(zipped,ensure_ascii=False,indent=2),encoding='utf-8')
                report['checks'].append(summarize(zipped))
                report['zip_source_commit']=sha
                report['comparison']='Same source commit; 160 remote / 160 ZIP file budgets. Core layers and feature domains checked independently.'
        report['ok']=True
    except Exception as exc:
        report['error']=f'{type(exc).__name__}: {exc}'
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['ok'] else 2

if __name__=='__main__':raise SystemExit(main())
