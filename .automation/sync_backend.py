"""One-time reviewed source update. Abort on any unexpected file hash.
No target-repository files or instructions are executed by this publisher.
"""
from pathlib import Path
import hashlib
EDITS = [
('app/__init__.py', '3e87a63fa90cd498d6228505b91554e41b5bbf5895130ef7e01e395ab4144cd6', '7375bcb486ad27d8a61e9c1df3e9718ee4bb619ccbfdf1c9a90844926e1c4b10', [
(1,2, r'''__version__ = "0.3.0"
'''),
]),
('app/extractor.py', '0cef23deb5d34d4d90faf1e0b1a7b2ddf37cfbb59ede73b58e303c503724bb38', 'f39950782b309a5955722744d1b7bb83e868d8dd7b5c82aa6282fd254258fc0a', [
(37,37, r'''        elif text[i] == '/' and (
            not text[:i].rstrip() or text[:i].rstrip()[-1] in '=(:,[!&|?{;'
            or re.search(r'\b(?:return|throw|case)\s*$', text[:i])
        ):
            # Common regex literal positions, not division. Mask escaped slashes
            # and character classes so /fakeCall()/ never creates a call edge.
            j=i+1;in_class=False
            while j<len(text) and text[j] not in '\n\r':
                if text[j]=='\\':j+=2;continue
                if text[j]=='[':in_class=True
                elif text[j]==']':in_class=False
                elif text[j]=='/' and not in_class:break
                j+=1
            if j<len(text) and text[j]=='/':
                j+=1
                while j<len(text) and text[j].isalpha():j+=1
                blank(i,j,True);i=j
            else:i+=1
'''),
(119,119, r'''        for m in matches(r"\b(?:baseUrl|baseURL|base_url)\s*=\s*['\"](https?://[^'\"\n]+)['\"]"):
            add(path,text,text.count('\n',0,m.start())+1,'config-url',m.group(1),'lexical')
'''),
]),
('app/graph.py', '5044933920b39a4a917499964c8ef4ac289de7b0a5bd5138c8916e8b855419f4', 'bd30d1871da121c9ccdbb9982c11a367c8391ce502cde5320a07812e955f6c34', [
(66,67, r'''    names=[('auth','Auth'),('fitrus','FITRUS'),('measurement','Measurement'),('algorithm','Algorithm'),('recommend','Recommendation'),('valid','Validation'),('storage','Storage'),('database','Storage'),('rule','Rules'),('session','Session'),('booking','Booking'),('feedback','Feedback')]
'''),
(128,129, r'''        elif f.kind in {'request','config-url'}:
'''),
(137,138, r'''                add_edge(source,nid,'config-url' if f.kind=='config-url' else 'http-url','candidate' if f.kind=='config-url' else 'confirmed',[f.evidence_id], '기본 URL 설정입니다. 환경별 실제 목적지나 요청 성공은 확인하지 않았습니다.' if f.kind=='config-url' else '코드에 절대 URL이 명시되어 있습니다. 해당 서비스를 호출하거나 가용성을 검사하지 않았습니다.')
'''),
(170,171, r'''            priorities={'Auth':0,'FITRUS':1,'Measurement':2,'Algorithm':2,'Validation':3,'Storage':4}
'''),
(245,246, r'''    result = Analysis(name=snapshot.name,source=snapshot.source,revision=snapshot.revision,repository_url=snapshot.repository_url,coverage=snapshot.coverage,
'''),
(248,248, r'''
    from .process import project_processes
    project_processes(result, snapshot)
    return result
'''),
]),
('app/intake.py', '913e750490ef964d53189f67ee07263c4c1132a643ea8a6477fcf43795c36fe8', '85f4fcf189009ab66329e0403033739f828da718d04c8369ef51b886a7e8d76f', [
(16,17, r'''MAX_REMOTE_FILES = 160
'''),
]),
('app/models.py', '33fa9f5c9e7e29e9e612f38c2512379be2b02682b80e1497a627acd346c5a926', 'e53853faa603c8d291a8d6e3e33b3b7067b4808e67ec12c94befe4240bb07066', [
(52,53, r'''    kind: Literal["import", "route", "request", "symbol", "config-url"]
'''),
(79,79, r'''class CallSite(Model):
    name: str
    evidence_id: str
    callee_id: str = ""
    resolution: Literal["unresolved", "static-candidate"] = "unresolved"

class ProcessStep(Model):
    id: str
    label: str
    category: str
    line: int
    end_line: int
    evidence_ids: list[str]
    node_ids: list[str]
    calls: list[CallSite] = Field(default_factory=list)
    conditional: bool = False
    description: str = "식별자·문장 형태 기반 요약 · 실제 실행 미검증"

class ProcessFlow(Model):
    id: str
    label: str
    path: str
    line: int
    end_line: int
    kind: Literal["route", "function", "sdk"]
    node_ids: list[str]
    evidence_ids: list[str]
    steps: list[ProcessStep]
    order: Literal["source-order"] = "source-order"
    warnings: list[str] = Field(default_factory=list)

'''),
(80,80, r'''    flow_ids: list[str] = Field(default_factory=list)
'''),
(105,106, r'''    flows: list[ProcessFlow] = Field(default_factory=list)
    schema_version: str = "1.1"
'''),
]),
('app/verifier.py', 'f52901cdcd3d3a0eb41d56cdd7f272ff23d949c3656334aab7059d80f80cc9c1', '6e8d04436fb09937d615c990b7599d2d69f7f5bb1fa8d8abc3036c4ed86c5805', [
(40,40, r'''
    flows={f.id:f for f in result.flows}
    if len(flows)!=len(result.flows): raise VerificationError('중복 처리 지도 ID')
    step_ids=set()
    for flow in result.flows:
        if flow.path not in files or not (1<=flow.line<=flow.end_line<=len(files[flow.path])):
            raise VerificationError('처리 지도 범위 오류')
        if flow.order!='source-order': raise VerificationError('미검증 실행 순서')
        if not flow.node_ids or not set(flow.node_ids)<=set(nodes): raise VerificationError('처리 지도 파일 누락')
        if not flow.evidence_ids or not set(flow.evidence_ids)<=set(ev): raise VerificationError('처리 지도 근거 누락')
        previous=flow.line
        for step in flow.steps:
            if step.id in step_ids:raise VerificationError('중복 처리 단계 ID')
            step_ids.add(step.id)
            if not (flow.line<=step.line<=step.end_line<=flow.end_line) or step.line<previous:
                raise VerificationError('처리 단계 순서/범위 오류')
            previous=step.line
            if not step.evidence_ids or not set(step.evidence_ids)<=set(flow.evidence_ids):raise VerificationError('처리 단계 근거 누락')
            if not set(step.node_ids)<=set(flow.node_ids):raise VerificationError('처리 단계 소속 오류')
            for eid in step.evidence_ids:
                e=ev[eid]
                if e.path!=flow.path or not (step.line<=e.line<=step.end_line):raise VerificationError('처리 단계 범위 밖 근거')
            for call in step.calls:
                if call.evidence_id not in step.evidence_ids:raise VerificationError('호출 위치 근거 없음')
                if call.callee_id and (call.callee_id not in flows or call.resolution!='static-candidate'):
                    raise VerificationError('호출 대상 없음/실행 확정 과장')
    for feature in result.features:
        if not set(feature.flow_ids)<=set(flows):raise VerificationError('기능 처리 지도 누락')
'''),
]),
('scripts/browser_smoke.py', '6929f514dee9b11a3d84f1fdfcf94bcedda9afbf3526f18a5ed4c93da015c3b1', 'b0bad7ab2f9029daf55ca9064fb483858d2a636600e110b96416944983ff7af3', [
(50,51, r'''        assert 1 <= page.locator('#graph [data-node]').count() <= 8
        assert page.locator('#processTools').is_visible()
        page.locator('#processTools [data-detail="files"]').click()
'''),
(70,71, r'''        assert json.loads(exports[0])['schema_version']=='1.1'
'''),
]),
('scripts/live_github_check.py', '247bcd6c1263de77f71c5d0270f405721fbf4bbe4815b6e6186413d803adf25b', '472c33091fb27b7e07a2bebf798e29e5d3369f61b5147de6e4052bb94188c97a', [
(33,33, r'''        from acceptance_flow import validate_semantics
        validate_semantics(result)
'''),
(74,75, r'''                report['comparison']='Same source commit; 160 remote / 160 ZIP file budgets. Core layers and feature domains checked independently.'
'''),
]),

]
staged={}
for name,before,after,edits in EDITS:
    path=Path(name);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()==after:continue
    assert hashlib.sha256(raw).hexdigest()==before, 'Unexpected source: '+name
    lines=raw.decode('utf-8').splitlines(keepends=True)
    for start,end,value in reversed(edits):lines[start:end]=[value]
    result=''.join(lines).encode('utf-8')
    assert hashlib.sha256(result).hexdigest()==after, 'Edited content mismatch: '+name
    staged[path]=result
for path,result in staged.items():path.write_bytes(result)
print('Applied',len(staged),'checksum-verified source changes')
