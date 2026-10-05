"""Meaning-level acceptance on VibeCare source, never target execution.
Project-specific expectations live HERE (test harness), never in the analyzer.
"""
from __future__ import annotations
import argparse,asyncio,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.models import Snapshot
from app.orchestrator import analyze_snapshot


def validate_semantics(r: dict) -> list[str]:
    checks=[];flows={f['id']:f for f in r['flows']};nodes={n['id']:n for n in r['nodes']}
    health=next(f for f in r['features'] if 'GET /health' in f['endpoint_labels'])
    assert len(health['node_ids'])==1,'Health still drags unrelated files'
    hf=flows[health['flow_ids'][0]]
    assert len(hf['steps'])==1 and hf['steps'][0]['category']=='response'
    checks.append('Health: one response operation / one related file')
    rec=next(f for f in r['features'] if 'POST /v1/recommendations/authorize' in f['endpoint_labels'])
    rf=next(flows[i] for i in rec['flow_ids'] if flows[i]['label']=='POST /v1/recommendations/authorize')
    call=next(c for s in rf['steps'] for c in s['calls'] if c['name']=='calculateRecommendation')
    algorithm=flows[call['callee_id']]
    assert algorithm['path']=='backend-api/src/algorithm.ts'
    assert call['resolution']=='static-candidate'
    checks.append('Recommendation route expands calculateRecommendation in its imported source')
    categories=[s['category'] for s in algorithm['steps']]
    for category in ('validate','safety','classify','select','adjust','response'):assert category in categories,category
    assert categories.index('safety')<categories.index('classify'),'Do not rearrange safety checks into an invented business flow'
    checks.append('Actual algorithm reading order retains validation and safety before classification')
    muscle=next(c for s in algorithm['steps'] for c in s['calls'] if c['name']=='skeletalMuscleLevel')
    assert flows[muscle['callee_id']]['label']=='skeletalMuscleLevel'
    checks.append('Classification opens its real index-calculation body')
    pin=next(f for f in r['features'] if 'POST /v1/auth/pin' in f['endpoint_labels'])
    assert len(pin['flow_ids'])==2
    sdk=next(f for f in r['features'] if f['label']=='Supabase 직접 인증')
    assert {'이메일 로그인','회원가입','로그아웃'}<={flows[i]['label'] for i in sdk['flow_ids']}
    assert not set(pin['flow_ids'])&set(sdk['flow_ids'])
    checks.append('Backend PIN/refresh and direct Supabase SDK variants stay separate')
    external=next(n for n in r['nodes'] if n['label']=='api.thefitrus.com')
    edges=[e for e in r['edges'] if e['target']==external['id']]
    assert edges and all(e['confidence']=='candidate' for e in edges)
    checks.append('FITRUS default URL present but not asserted as a live/proven request')
    assert len(r['system_nodes'])<=8
    assert r['coverage']['analyzed']==r['coverage']['eligible'] and not r['coverage']['partial']
    for flow in r['flows']:
        assert flow['order']=='source-order' and flow['warnings']
        for step in flow['steps']:
            assert step['evidence_ids'] and all(nodes[n]['path']==flow['path'] for n in step['node_ids'])
    checks.append('All selected supported files read; every process step belongs to source evidence')
    return checks

async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--snapshot',required=True);parser.add_argument('--output',default='evidence/acceptance')
    args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    snapshot=Snapshot.model_validate_json(Path(args.snapshot).read_text(encoding='utf-8'))
    result=(await analyze_snapshot(snapshot)).model_dump()
    checks=validate_semantics(result)
    (out/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'ok':True,'checks':checks,'count':len(checks),'target_revision':snapshot.revision,'coverage':result['coverage'],'flows':len(result['flows']),'features':len(result['features'])}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':asyncio.run(main())
