"""Evidence-backed processing view over the SAME source/file graph.
No project-name fixtures or LLM-generated steps. Labels are deterministic
interpretations of identifiers; edges mean source reading order, not execution.
"""
from __future__ import annotations
import ast
import re
from collections import defaultdict
from urllib.parse import quote
from .models import Analysis, Snapshot, Evidence, ProcessFlow, ProcessStep, CallSite, Feature
from .extractor import masks, stable_id
from .flow_scanner import Scope, lexical_scopes, python_scopes, line_at, matching, source_masks
from .graph import resolve_import

LABELS={
 'auth':'인증 확인', 'validate':'입력·조건 검증', 'read':'데이터 조회',
 'rules':'규칙 불러오기', 'normalize':'데이터 정규화', 'calculate':'계산 수행',
 'recommend':'추천 계산', 'classify':'등급 분류', 'safety':'안전 조건 확인',
 'adjust':'강도·계수 조정', 'write':'데이터 저장', 'network':'외부 요청',
 'token':'토큰·허가 발급', 'response':'결과 반환', 'prepare':'값 준비',
 'select':'설정 선택', 'sdk-auth':'SDK 인증 호출', 'condition':'조건 분기',
}
SDK_AUTH=re.compile(r'\.auth\.(signInWithPassword|signUp|signOut|refreshSession|resetPasswordForEmail)\s*\(')


def classify_statement(code: str, nc: str, calls: list[str]) -> str:
    names=' '.join(calls)
    first=code.strip()
    if first.startswith(('return','raise','throw')):return 'response'
    if SDK_AUTH.search(code):return 'sdk-auth'
    # Conditional checks precede effects, and their outcomes are shown in evidence.
    if re.match(r'(if|for|while|switch)\b',first):
        par=code.find('(');end=matching(code,par) if par>=0 else None
        condition=code[:end+1] if end is not None else code
        if re.search(r'safety|acutePain|dizziness|clinicianHold|physicalExecution|simulationEligibility|DEVICE_MODE|mode\s*!==|intensityCap',condition,re.I):return 'safety'
        if re.search(r'!\s*participantId\b|verifyToken|verifyPin|!\s*token\b',condition,re.I):return 'auth'
        return 'validate'
    checks=[('sdk-auth',r'\.auth\.'),('rules',r'loadRule|readRule|fetchRule'),
            ('token',r'issueToken|createSession|signToken'),('auth',r'accessParticipant|verifyToken|verifyPin|authenticate|signIn|login'),
            ('validate',r'validat|safeParse|parseFitrus|jsonBody'),('normalize',r'normaliz|canonical'),
            ('recommend',r'calculateRecommend'),('classify',r'classif|MuscleLevel'),
            ('adjust',r'Coefficient|RequestedIntensity|clamp'),('safety',r'safety|safetyWarnings'),
            ('read',r'load|read|\.query|\.prepare|\.select|\.first|\.all\b'),
            ('network',r'fetch|\.get\b|\.post\b|\.measure\b'),('calculate',r'calculat|mean\b|round\b'),
            ('write',r'\.insert|\.update|\.delete|\.batch|save|persist')]
    if re.match(r'try\b',first) and re.search(r'fetch|\.measure\b',names):return 'network'
    if re.search(r'\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b',nc,re.I) and re.search(r'\.prepare|\.query',names):return 'write'
    for kind,pattern in checks:
        if re.search(pattern,names,re.I):return kind
    # For assignments without calls, distinguish visible operations from inventions.
    lhs=re.match(r'\s*(?:const|let|var|final)?\s*([A-Za-z_$]\w*)\s*(?::[^=;]+)?=',code)
    if lhs:
        var=lhs.group(1)
        if re.search('safety',var,re.I):return 'safety'
        if re.search(r'\?|\[',code) and re.search('base|setting|threshold',var,re.I):return 'select'
        if re.search('coefficient|intensity|factor',var,re.I):return 'adjust'
        if re.search(r'(?<![*/])[*+/](?![*/])',code):return 'calculate'
    if re.search(r'\.(json|send)\s*\(',code):return 'response'
    return 'prepare'


def project_processes(result: Analysis, snapshot: Snapshot) -> None:
    files={f.path:f.content for f in snapshot.files};file_nodes={n.path:n for n in result.nodes if n.kind=='file'}
    path_facts=defaultdict(list)
    for f in result.facts:path_facts[f.path].append(f)
    scopes=[];masked={};imports={};roots={}
    for path,text in files.items():
        if path.endswith('pubspec.yaml'):
            m=re.search(r'^name:\s*([\w-]+)',text,re.M)
            if m:roots[m.group(1)]=path.rsplit('/',1)[0] if '/' in path else '.'
    for path,node in file_nodes.items():
        text=files[path];masked[path]=source_masks(path,text)
        scopes.extend(python_scopes(path,text,path_facts[path]) if path.endswith('.py') else lexical_scopes(path,text,path_facts[path]))
        binding={}
        if path.endswith('.py'):
            try:
                tree=ast.parse(text)
                for stmt in tree.body:
                    if isinstance(stmt,ast.ImportFrom):
                        target=resolve_import(path,'.'*stmt.level+(stmt.module or ''),set(file_nodes),roots)
                        for alias in stmt.names:
                            if target:binding[alias.asname or alias.name]=(target,alias.name)
            except (SyntaxError,RecursionError):pass
        else:
            nc,code=masked[path]
            for m in re.finditer(r'\bimport\s*\{([^}]+)\}\s*from\s*[\'\"]([^\'\"]+)[\'\"]',nc):
                if not code[m.start():m.start()+6].strip():continue
                target=resolve_import(path,m.group(2),set(file_nodes),roots)
                if target:
                    for name in m.group(1).split(','):
                        bits=re.sub(r'^\s*type\s+','',name.strip()).split(' as ')
                        if bits and re.fullmatch(r'\w+',bits[0]):binding[bits[-1].strip()]=(target,bits[0])
        imports[path]=binding
    sdk_labels={}
    for path,(nc,code) in masked.items():
        if not any('supabase' in f.value.lower() for f in path_facts[path] if f.kind=='import'):continue
        for m in SDK_AUTH.finditer(code):
            par=m.end()-1;end=matching(code,par)
            if end is None:continue
            start=m.start()
            while start>0 and re.match(r'[\w$.]',code[start-1]):start-=1
            label={'signInWithPassword':'이메일 로그인','signUp':'회원가입','signOut':'로그아웃','refreshSession':'세션 갱신','resetPasswordForEmail':'비밀번호 재설정'}[m.group(1)]
            scope=Scope(stable_id('sdk-flow',path,str(start)),path,label,start,start,end+1,'sdk')
            scope.statements=[(start,end+1)];scope.calls=[(start,code[start:m.end()-1].strip())]
            scopes.append(scope);sdk_labels[scope.id]=label
    # IDs and scopes, not globally matching function names.
    scopes_by_id={s.id:s for s in scopes};named=defaultdict(list)
    for s in scopes:
        if s.kind=='function':named[(s.path,s.name)].append(s)
    ev={e.id:e for e in result.evidence}
    def evidence(s: Scope,at: int,end: int|None=None,kind='operation') -> str:
        text=files[s.path];line=line_at(text,at);last=min(line+3,line_at(text,max(at,(end or at+1)-1)))
        eid=stable_id('ev-scope',s.path,str(line),str(last),kind)
        url=f'{snapshot.repository_url}/blob/{snapshot.revision}/{quote(s.path,safe="/")}#L{line}-L{last}' if snapshot.repository_url else ''
        ev[eid]=Evidence(id=eid,path=s.path,line=line,end_line=last,snippet='\n'.join(text.splitlines()[line-1:last]),kind=kind,parser=s.parser,url=url)
        return eid
    def resolve(s: Scope,name: str) -> str:
        if name.startswith('new:'):
            cls,_,method=name[4:].partition('.')
            target=imports[s.path].get(cls)
            target_path,target_class=target if target else (s.path,cls)
            choices=[t for t in named[(target_path,method)] if t.class_name==target_class]
            return choices[0].id if len(choices)==1 else ''
        if '.' in name:
            # A locally constructed class instance can resolve a method candidate.
            owner,_,method=name.rpartition('.')
            if not re.fullmatch(r'\w+',owner):return ''
            declaration=re.search(r'\b(?:const|let|final)\s+'+re.escape(owner)+r'\s*=\s*new\s+(\w+)\s*\(',masked[s.path][1][s.body:s.end])
            if not declaration:return ''
            cls=declaration.group(1);target=imports[s.path].get(cls)
            target_path,target_class=target if target else (s.path,cls)
            choices=[t for t in named[(target_path,method)] if t.class_name==target_class]
            return choices[0].id if len(choices)==1 else ''
        if not re.fullmatch(r'[\w$]+',name) or name in s.parameters:return '' 
        nc,code=masked[s.path]
        if re.search(r'\b(?:const|let|var|final)\s+'+re.escape(name)+r'\b',code[s.body:s.end]):return ''
        if s.path.endswith('.py') and re.search(r'(?m)^\s*'+re.escape(name)+r'\s*(?::[^=\n]+)?=(?!=)',code[s.body:s.end]):return ''
        candidates=[]
        for t in named[(s.path,name)]:
            if t.class_name:continue
            parent=next((p for p in sorted(scopes,key=lambda p:p.end-p.start) if p.path==t.path and p.id!=t.id and p.body<=t.start<p.end),None)
            if parent is None or parent.body<=s.start<parent.end or parent.id==s.id:candidates.append(t)
        if len(candidates)==1:return candidates[0].id
        if candidates:return ''
        imported=imports[s.path].get(name)
        if imported:
            ts=[t for t in named[imported] if not t.class_name]
            if len(ts)==1:return ts[0].id
        return ''
    flows={};sdk_features=defaultdict(list)
    for s in scopes:
        node=file_nodes[s.path];text=files[s.path];nc,code=masked[s.path]
        steps=[];prev=None
        child_scopes=[t for t in scopes if t.path==s.path and s.body<=t.start<s.end and t.id!=s.id and t.kind!='sdk']
        for start,end in s.statements:
            # Nested declarations and registered endpoints are not caller execution.
            if any(t.start<=start and end<=t.end+3 for t in child_scopes):continue
            fragment=code[start:end];clean=nc[start:end]
            if not fragment.strip():continue
            calls=[]
            for at,name in s.calls:
                if start<=at<end:
                    callee=resolve(s,name)
                    calls.append(CallSite(name=name,evidence_id=evidence(s,at),callee_id=callee,resolution='static-candidate' if callee else 'unresolved'))
            category=classify_statement(fragment,clean,[c.name for c in calls])
            conditional=bool(re.search(r'\b(if|for|while|try|catch|switch)\b|\?|=>',fragment))
            eids=list(dict.fromkeys([evidence(s,start,end)]+[c.evidence_id for c in calls]))
            # Include later return/throw sites, otherwise a long guard could hide its exit.
            for exit_match in re.finditer(r'\b(return|throw|raise)\b',fragment):
                eids.append(evidence(s,start+exit_match.start(),kind='exit'))
            if category=='prepare' and prev is not None:
                category=prev.category
            if prev is not None and (category==prev.category or prev.category=='prepare'):
                if prev.category=='prepare':prev.category=category;prev.label=LABELS[category]
                prev.end_line=line_at(text,max(start,end-1));prev.evidence_ids=list(dict.fromkeys(prev.evidence_ids+eids));prev.calls.extend(calls);prev.conditional|=conditional
            else:
                prev=ProcessStep(id=stable_id('step',s.id,str(start)),label=LABELS[category],category=category,line=line_at(text,start),end_line=line_at(text,max(start,end-1)),evidence_ids=list(dict.fromkeys(eids)),node_ids=[node.id],calls=calls,conditional=conditional)
                steps.append(prev)
        if not steps:continue
        kind=s.kind
        if s.id in sdk_labels:
            kind='sdk';sdk_features['Supabase 직접 인증'].append(s.id)
        evidence_ids=list(dict.fromkeys([evidence(s,s.start,s.body,kind='scope')]+[e for step in steps for e in step.evidence_ids]))
        flows[s.id]=ProcessFlow(id=s.id,label=s.name,path=s.path,line=line_at(text,s.start),end_line=line_at(text,max(s.body,s.end-1)),kind=kind,node_ids=[node.id],evidence_ids=evidence_ids,steps=steps,warnings=['소스의 읽기 순서입니다. 분기·반복·조기반환·콜백 때문에 모든 단계가 순서대로 실행되는 것은 아닙니다.','단계명은 식별자·문장 형태에 따른 규칙 기반 해석입니다. 보안·업무 의미를 증명하지 않습니다.'])
    # Remove targets for unsupported/empty function bodies; NEVER invent a callee.
    for flow in flows.values():
        for step in flow.steps:
            for c in step.calls:
                if c.callee_id not in flows:c.callee_id='';c.resolution='unresolved'
    route_index=defaultdict(list)
    for s in scopes:
        if s.kind=='route' and s.id in flows:route_index[(s.path,s.method+' '+s.endpoint)].append(s.id)
    for f in result.features:
        f.flow_ids=[sid for (path,ep),ids in route_index.items() if ep in f.endpoint_labels and file_nodes[path].id in f.node_ids for sid in ids]
        if not f.flow_ids:
            f.warnings.append('라우트 본문 범위를 해석하지 못했습니다. 처리 순서를 만들지 않고 파일 참고도만 제공합니다.')
    for label,ids in sdk_features.items():
        node_ids=sorted({file_nodes[flows[i].path].id for i in ids}|({'infra-supabase'} if any(n.id=='infra-supabase' for n in result.nodes) else set()))
        f=Feature(id=stable_id('feature',label),label=label,description='Backend PIN/refresh API와 별개인 SDK 직접 인증 경로',endpoint_labels=['SDK · auth'],node_ids=node_ids,edge_ids=[],component_ids=[],flow_ids=ids,warnings=[])
        result.features.insert(0,f)
    # Reachable scope dependencies replace the old radius-based file expansion.
    by_id={n.id:n for n in result.nodes};kept=set()
    for feature in result.features:
        if not feature.flow_ids:continue
        selected=set();todo=[(i,0) for i in feature.flow_ids];visited=set();limit=False
        while todo:
            fid,depth=todo.pop()
            if fid in visited:continue
            visited.add(fid);kept.add(fid);flow=flows[fid];scope=scopes_by_id[fid];selected.update(flow.node_ids)
            fragment=masked[flow.path][1][scope.body:scope.end]
            for binding,(target,_) in imports[flow.path].items():
                if re.search(r'\b'+re.escape(binding)+r'\b',fragment):selected.add(file_nodes[target].id)
            for n in result.nodes:
                if n.kind=='infrastructure' and any(e.source==file_nodes[flow.path].id and e.target==n.id for e in result.edges):
                    if n.id=='infra-supabase' and not re.search(r'\bSupabase\b|\.auth\.|\.from\(',fragment):continue
                    selected.add(n.id)
            for step in flow.steps:
                for call in step.calls:
                    if call.callee_id:
                        if depth<5:todo.append((call.callee_id,depth+1))
                        else:limit=True
        # Only matching method/path requests, not every request to the same source file.
        eps=set(feature.endpoint_labels)
        for fact in result.facts:
            if fact.kind=='request' and fact.method+' '+fact.value in eps and fact.path in file_nodes:selected.add(file_nodes[fact.path].id)
        feature.node_ids=sorted(selected)
        feature.edge_ids=[e.id for e in result.edges if e.source in selected and e.target in selected and (e.relation!='http-contract' or any(ev[x].kind=='route' and any(f.evidence_id==x and f.method+' '+f.value in eps for f in result.facts) for x in e.evidence_ids))]
        feature.component_ids=sorted({by_id[n].component_id for n in selected})
        feature.description='API별 본문 → 처리 단계 → 함수·파일 근거'
        feature.warnings=['본문과 직접 참조에 근거한 범위입니다. 간접 호출·동적 메서드·미들웨어는 완전하게 추적하지 않습니다.','파일 참고도의 import는 실행 순서가 아닙니다. HTTP 연결은 origin 미확인 후보입니다.']
        if limit:feature.warnings.append('함수 확장 깊이 5에 도달했습니다. 더 깊은 연결은 별도 검토가 필요합니다.')
    # Keep callee targets for expansion beyond the initial feature slice (cycle-safe).
    queue=list(kept)
    while queue:
        fid=queue.pop()
        for step in flows[fid].steps:
            for call in step.calls:
                if call.callee_id and call.callee_id not in kept:kept.add(call.callee_id);queue.append(call.callee_id)
    result.flows=[flow for fid,flow in flows.items() if fid in kept]
    used={eid for f in result.flows for eid in f.evidence_ids}
    result.evidence.extend(e for eid,e in ev.items() if eid in used and eid not in {x.id for x in result.evidence})
    result.summary=f'{snapshot.coverage.analyzed}개 파일 · {len(result.system_nodes)-1}개 핵심 영역 · {len(result.features)}개 기능 · 본문 기반 처리 지도 {len(result.flows)}개. 정적 분석이며 실행 관측이 아닙니다.'
