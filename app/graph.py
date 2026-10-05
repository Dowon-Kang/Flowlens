"""Create one evidence graph, then project it into system and feature views."""
from __future__ import annotations
import posixpath
import re
from collections import defaultdict, deque
from pathlib import PurePosixPath
from urllib.parse import urlparse
from .models import Analysis, Snapshot, Fact, Evidence, Node, Edge, Feature
from .extractor import stable_id
from .intake import SOURCE_SUFFIXES

INFRA = {'supabase': ('Supabase', '인증·데이터 SDK · 배포 상태 미확인'),
         'postgres': ('PostgreSQL client', 'PostgreSQL 드라이버 · 호스트 미확인'),
         'sqlite': ('SQLite', '코드에서 확인된 SQLite 접근'),
         'redis': ('Redis client', 'Redis 클라이언트 · 연결 성공 미검증'),
         'openai': ('OpenAI SDK', '모델 API 클라이언트 · 호출 성공 미검증')}

def infra_key(module: str) -> str | None:
    m=module.lower()
    if 'supabase' in m: return 'supabase'
    if m in {'pg','postgres','psycopg','psycopg2','asyncpg'}: return 'postgres'
    if m in {'sqlite3','better-sqlite3','sqlite'}: return 'sqlite'
    if m in {'redis','ioredis'}: return 'redis'
    if m in {'openai','@openai/agents'}: return 'openai'
    return None

def resolve_import(path: str, module: str, paths: set[str], package_roots: dict[str,str]) -> str | None:
    suffix=PurePosixPath(path).suffix
    if suffix=='.py':
        if module.startswith('.'):
            n=len(module)-len(module.lstrip('.'))
            base=PurePosixPath(path).parent
            for _ in range(n-1): base=base.parent
            guess=posixpath.normpath(str(base / module.lstrip('.').replace('.', '/')))
        else:
            guess=module.replace('.', '/')
        variants=[guess+'.py',guess+'/__init__.py']
    else:
        if module.startswith('.'):
            guess=posixpath.normpath(str(PurePosixPath(path).parent / module))
        elif module.startswith('package:') and module[8:].split('/')[0] in package_roots:
            name,_,tail=module[8:].partition('/')
            guess=package_roots[name]+'/lib/'+tail
        else:
            return None
        variants=[guess,guess+'.ts',guess+'.tsx',guess+'.js',guess+'.jsx',guess+'.dart',guess+'/index.ts',guess+'/index.js',guess+'/index.tsx']
        if guess.endswith('.js'):
            variants.extend([guess[:-3]+'.ts',guess[:-3]+'.tsx'])
    return next((v for v in variants if not v.startswith('../') and v in paths),None)

def classify(path: str, imports: list[str]) -> str:
    p=path.lower(); imp=' '.join(imports).lower()
    frontend=path.endswith('.dart') or bool(re.search(r'(^|/)(client|frontend|mobile-app|web|screens|components|pages|ui)(/|$)',p)) or any(x in imp for x in ['react','flutter'])
    if frontend:
        if re.search(r'controller|provider|store|state|hooks?/',p): return 'state'
        if re.search(r'service|repository|client|api[_/-]',p) and not re.search(r'(screen|view|component|\.tsx|\.jsx)',p): return 'transport'
        return 'app'
    if path.endswith('.py') or re.search(r'backend|server|routes?|services?|(^|/)api/',p) or any(x in imp for x in ['hono','fastapi','express','flask']):
        return 'backend'
    return 'modules'

def technology(imports: list[str], needle: str) -> bool:
    return any(needle in m.lower() for m in imports)

def module_tag(path: str) -> str:
    p=path.lower()
    names=[('auth','Auth'),('measurement','Measurement'),('algorithm','Algorithm'),('recommend','Recommendation'),('valid','Validation'),('storage','Storage'),('database','Storage'),('rule','Rules'),('session','Session'),('booking','Booking'),('feedback','Feedback')]
    return next((label for text,label in names if text in p),PurePosixPath(path).stem.replace('_',' ').replace('-',' ').title())

def build_analysis(snapshot: Snapshot, facts: list[Fact], evidence: list[Evidence], warnings: list[str]) -> Analysis:
    source_files=[f for f in snapshot.files if PurePosixPath(f.path).suffix in SOURCE_SUFFIXES]
    paths={f.path for f in source_files}
    by_path: dict[str,list[Fact]]=defaultdict(list)
    for fact in facts: by_path[fact.path].append(fact)
    all_imports=[f.value for f in facts if f.kind=='import']
    nodes: dict[str,Node]={}
    edges: dict[str,Edge]={}
    path_ids={p:stable_id('file',p) for p in paths}
    output_warnings=list(snapshot.warnings)+list(warnings)
    package_roots={}
    for f in snapshot.files:
        if PurePosixPath(f.path).name=='pubspec.yaml':
            match=re.search(r'^name:\s*([\w-]+)',f.content,re.M)
            if match: package_roots[match.group(1)]=str(PurePosixPath(f.path).parent)
    evidence_map={e.id:e for e in evidence}
    for file in source_files:
        pf=by_path[file.path]
        eids=list(dict.fromkeys(f.evidence_id for f in pf))
        if not eids:
            # Files without recognized syntax still have honest, exact source evidence.
            lines=file.content.splitlines()
            if not lines: continue
            line=next((i+1 for i,x in enumerate(lines) if x.strip()),1)
            eid=stable_id('ev',file.path,str(line),'source')
            e=Evidence(id=eid,path=file.path,line=line,end_line=line,snippet=lines[line-1],kind='source',parser='ast' if file.path.endswith('.py') else 'lexical')
            evidence_map[eid]=e; eids=[eid]
        role=classify(file.path,[f.value for f in pf if f.kind=='import'])
        nid=path_ids[file.path]
        nodes[nid]=Node(id=nid,label=PurePosixPath(file.path).name,kind='file',component_id='system-'+role,role=role,path=file.path,
                       description='정적 소스 파일 · 실행 여부는 검증하지 않음',evidence_ids=eids,
                       tags=list(dict.fromkeys(f.value for f in pf if f.kind=='symbol'))[:6])
    def add_edge(source: str,target: str,relation: str,confidence: str,eids: list[str],description: str):
        if source==target or source not in nodes or target not in nodes: return
        eid=stable_id('edge',source,target,relation)
        if eid in edges:
            edges[eid].evidence_ids=list(dict.fromkeys(edges[eid].evidence_ids+eids))
        else:
            edges[eid]=Edge(id=eid,source=source,target=target,relation=relation,confidence=confidence,evidence_ids=list(dict.fromkeys(eids)),description=description)
    unresolved=[]
    for f in facts:
        source=path_ids.get(f.path)
        if source not in nodes: continue
        if f.kind=='import':
            target=resolve_import(f.path,f.value,paths,package_roots)
            if target and path_ids.get(target) in nodes:
                add_edge(source,path_ids[target],'import','confirmed',[f.evidence_id],f'정적 import: {f.value}. 함수 호출 순서나 실행 성공은 미검증입니다.')
            else:
                key=infra_key(f.value)
                if key:
                    nid='infra-'+key
                    label,desc=INFRA[key]
                    if nid not in nodes:
                        nodes[nid]=Node(id=nid,label=label,kind='infrastructure',component_id='system-'+nid,role='infrastructure',description=desc,evidence_ids=[f.evidence_id])
                    else:
                        nodes[nid].evidence_ids.append(f.evidence_id)
                    add_edge(source,nid,'sdk','confirmed',[f.evidence_id],f'SDK/드라이버 import: {f.value}. 실제 배포 위치/연결 성공은 미확인입니다.')
                elif f.value.startswith(('.', '@/','~/')):
                    unresolved.append(f'{f.path}: {f.value}')
        elif f.kind=='request':
            parsed=urlparse(f.value)
            if parsed.scheme in {'https','http'} and parsed.hostname:
                host=parsed.hostname
                # Hardcoded URLs are evidence, never fetched by the analyzer.
                nid=stable_id('external',host)
                if nid not in nodes:
                    nodes[nid]=Node(id=nid,label=host,kind='infrastructure',component_id='system-'+nid,role='infrastructure',description='코드에 명시된 외부 HTTP 목적지 · 실제 연결 미검증',evidence_ids=[f.evidence_id])
                else: nodes[nid].evidence_ids.append(f.evidence_id)
                add_edge(source,nid,'http-url','confirmed',[f.evidence_id],'코드에 절대 URL이 명시되어 있습니다. 해당 서비스를 호출하거나 가용성을 검사하지 않았습니다.')
    # Match exact contract shape. Different origins may use identical paths: candidates only.
    routes=[f for f in facts if f.kind=='route']
    for req in (f for f in facts if f.kind=='request' and f.method in {'GET','POST','PUT','PATCH','DELETE','OPTIONS','HEAD'}):
        requested=urlparse(req.value).path
        for route in routes:
            if req.path != route.path and requested==route.value and req.method==route.method:
                add_edge(path_ids[req.path],path_ids[route.path],'http-contract','candidate',[req.evidence_id,route.evidence_id],
                         f'{req.method} {requested} 일치. base URL, route prefix, 프록시, 배포 환경을 검증하지 않은 연결 후보입니다.')
    if unresolved:
        output_warnings.append(f'로컬 import {len(unresolved)}건을 해석하지 못했습니다(제외/누락/alias 가능): '+ '; '.join(unresolved[:4]))
    if any(e.relation=='http-contract' for e in edges.values()):
        output_warnings.append('HTTP 점선은 method/path가 일치하는 연결 후보입니다. 실제 서버 origin과 런타임 연결을 확인하지 않았습니다.')
    if 'infra-supabase' in nodes and 'infra-postgres' in nodes:
        output_warnings.append('Supabase와 PostgreSQL 드라이버가 모두 발견되었습니다. 같은 DB인지 별도 DB인지는 코드 근거만으로 확정하지 않습니다.')
    labels={
        'app':'Flutter App' if technology(all_imports,'flutter') else 'React App' if technology(all_imports,'react') else 'Client App',
        'state':'Riverpod / Controller' if technology(all_imports,'riverpod') else 'State / Controller',
        'transport':'Service / Dio' if technology(all_imports,'dio') else 'Service / Axios' if technology(all_imports,'axios') else 'Service / HTTP',
        'backend':'Hono Backend' if technology(all_imports,'hono') else 'FastAPI Backend' if technology(all_imports,'fastapi') else 'Express Backend' if technology(all_imports,'express') else 'Backend Modules',
        'modules':'Application Modules',
    }
    desc={'app':'화면과 사용자 입력','state':'상태 관리와 동작 조정','transport':'클라이언트 서비스와 HTTP 요청','backend':'요청 처리와 핵심 기능','modules':'분류된 애플리케이션 모듈'}
    groups: dict[str,list[Node]]=defaultdict(list)
    for n in nodes.values(): groups[n.component_id].append(n)
    system_nodes=[]
    for cid,members in groups.items():
        role=members[0].role
        if role=='infrastructure':
            label=members[0].label; description=members[0].description; tags=[]
        else:
            label=labels[role];description=desc[role]
            tags=list(dict.fromkeys(module_tag(n.path) for n in members if role=='backend' and module_tag(n.path) not in {'Index','Main','App'}))
            priorities={'Auth':0,'Measurement':1,'Algorithm':2,'Validation':3,'Storage':4}
            tags=sorted(tags,key=lambda t:priorities.get(t,10))[:6]
        system_nodes.append(Node(id=cid,label=label,kind='component',role=role,description=description,
                                 evidence_ids=list(dict.fromkeys(e for n in members for e in n.evidence_ids)),member_ids=[n.id for n in members],tags=tags))
    # Preserve canonical entities while folding lower-priority infrastructure in the overview.
    if len(system_nodes)>7:
        infra_nodes=[n for n in system_nodes if n.role=='infrastructure']
        keep_count=max(1,7-(len(system_nodes)-len(infra_nodes))-1)
        fold=infra_nodes[keep_count:]
        if fold:
            fold_ids={n.id for n in fold}; members=[x for n in fold for x in n.member_ids]
            for nid in members: nodes[nid].component_id='system-other-infra'
            system_nodes=[n for n in system_nodes if n.id not in fold_ids]
            system_nodes.append(Node(id='system-other-infra',label=f'Other services · {len(fold)}',kind='component',role='infrastructure',description='전체 지도에서 접힌 외부 연동. 기능별 지도에서는 각각 표시합니다.',member_ids=members,evidence_ids=list(dict.fromkeys(e for n in fold for e in n.evidence_ids))))
    system_edges: dict[str,Edge]={}
    for e in edges.values():
        a,b=nodes[e.source].component_id,nodes[e.target].component_id
        if a==b: continue
        sid=stable_id('system-edge',a,b,e.relation)
        if sid in system_edges:
            current=system_edges[sid]
            current.evidence_ids=list(dict.fromkeys(current.evidence_ids+e.evidence_ids))
        else:
            system_edges[sid]=Edge(id=sid,source=a,target=b,relation=e.relation,confidence=e.confidence,evidence_ids=list(e.evidence_ids),description=e.description)
    order={'app':0,'state':1,'transport':2,'backend':3,'modules':4,'infrastructure':5}
    system_nodes.sort(key=lambda n:(order[n.role],n.label))
    if system_nodes:
        first=next((n for n in system_nodes if n.role in {'app','backend','modules'}),system_nodes[0])
        system_nodes.insert(0,Node(id='system-user',label='사용자 / 요청',kind='virtual',role='user',description='이해를 돕는 설명용 시작점. 실제 실행을 관측한 노드가 아닙니다.'))
        sid='system-entry'
        system_edges[sid]=Edge(id=sid,source='system-user',target=first.id,relation='entry-model',confidence='candidate',evidence_ids=first.evidence_ids[:1],description='설명용 진입점입니다. 인증/이벤트 진입 경로의 완전성을 보장하지 않습니다.')
    # Feature views are induced subgraphs, not newly generated diagrams.
    feature_routes: dict[str,list[Fact]]=defaultdict(list)
    for route in routes:
        parts=[x for x in route.value.split('/') if x and x not in {'api','v1','v2','v3'}]
        key=next((x for x in parts if not x.startswith((':','{'))),'root')
        feature_routes[key].append(route)
    feature_labels={'auth':'로그인 · 인증','measurements':'측정 데이터','recommendations':'추천','bookings':'예약','tasks':'할 일 관리','users':'사용자','sessions':'세션','feedback':'피드백'}
    features=[]
    forward=defaultdict(list); reverse=defaultdict(list)
    for e in edges.values(): forward[e.source].append(e);reverse[e.target].append(e)
    for key,items in feature_routes.items():
        selected={path_ids[r.path] for r in items if path_ids[r.path] in nodes}
        seeds=set(selected)
        # Downstream source dependencies, not a guaranteed sequence of function calls.
        q=deque((n,0) for n in selected)
        while q:
            nid,depth=q.popleft()
            if depth>=5: continue
            for e in forward[nid]:
                if e.target not in selected:
                    selected.add(e.target);q.append((e.target,depth+1))
        # Link incoming HTTP candidates and walk upstream through frontend imports only.
        incoming={e.source for n in seeds for e in reverse[n] if e.relation=='http-contract'}
        selected|=incoming;q=deque((n,0) for n in incoming)
        while q:
            nid,depth=q.popleft()
            if depth>=5: continue
            for e in reverse[nid]:
                if nodes[e.source].role in {'app','state','transport'} and e.source not in selected:
                    selected.add(e.source);q.append((e.source,depth+1))
        fw=[]
        if len(selected)>32:
            # Keep endpoints and order other nodes deterministically. Disclose pruning.
            selected=set(list(sorted(seeds))+[n for n in sorted(selected) if n not in seeds][:max(0,32-len(seeds))])
            fw.append('이 기능의 관련 노드가 많아 최대 32개로 제한했습니다.')
        fw.append('파일 단위 의존성 지도입니다. 한 파일 안의 다른 기능·분기와 동적 호출이 포함되거나 누락될 수 있습니다.')
        if not incoming: fw.append('연결되는 클라이언트 HTTP 요청을 찾지 못했습니다. 누락된 구간을 임의로 연결하지 않습니다.')
        f_edges=[e.id for e in edges.values() if e.source in selected and e.target in selected]
        features.append(Feature(id=stable_id('feature',key),label=feature_labels.get(key,key.replace('-',' ').title()),description=f'{key} API 주변의 코드 관계',
                                endpoint_labels=list(dict.fromkeys(f'{r.method} {r.value}' for r in items)),
                                node_ids=sorted(selected),edge_ids=f_edges,component_ids=list(dict.fromkeys(nodes[n].component_id for n in sorted(selected))),warnings=fw))
    if not features:
        output_warnings.append('지원 패턴의 API endpoint를 찾지 못했습니다. 기능별 흐름을 임의로 만들지 않았습니다.')
    summary=f'{len(source_files)}개 소스 파일을 {len(system_nodes)-1 if system_nodes else 0}개 핵심 영역으로 압축했습니다. {len(features)}개 API 기능을 탐색할 수 있습니다.'
    return Analysis(name=snapshot.name,source=snapshot.source,revision=snapshot.revision,repository_url=snapshot.repository_url,coverage=snapshot.coverage,
                    nodes=list(nodes.values()),edges=list(edges.values()),system_nodes=system_nodes,system_edges=list(system_edges.values()),features=features,
                    evidence=list(evidence_map.values()),facts=facts,warnings=list(dict.fromkeys(output_warnings)),summary=summary)
