"""Bounded UML-informed control-flow projection, NOT a runtime trace or full CFG.

All nodes refer to the SAME ProcessFlow/source/evidence graph. Existing steps
are retained as a source-order fallback. No target code, imports or expressions
are executed. Unsupported bodies fail closed instead of producing fake chains.
"""
from __future__ import annotations
import ast
import re
from dataclasses import dataclass, field
from typing import Callable
from .models import ActivityFlow, ActivityNode, ActivityEdge, ActivityCallRef, ProcessFlow
from .flow_scanner import Scope, matching, line_at
from .extractor import stable_id

MAX_NODES = 128
MAX_DEPTH = 24
ASSUMPTIONS = [
    '정적 UML 활동 부분 모델 · 실제 실행 미검증. 화살표는 지원 문법의 제어 흐름 후보입니다.',
    '표현식은 하나의 불투명한 작업입니다. 단락 평가·호출 내부·암묵적 예외·비동기 스케줄링은 모델링하지 않습니다.',
    '반환은 정상 종료, 명시적 raise/throw는 예외 전파 종료입니다. 호출자의 예외 처리나 전체 프로세스 종료를 뜻하지 않습니다.',
]

class Unsupported(ValueError):
    """A scope cannot safely be projected by the documented subset."""

@dataclass
class Statement:
    kind: str
    start: int
    end: int
    yes: list['Statement'] = field(default_factory=list)
    no: list['Statement'] = field(default_factory=list)


def python_body(text: str, scope: Scope, tree: ast.AST) -> list[Statement]:
    lines=text.splitlines(keepends=True);starts=[];offset=0
    for line in lines:starts.append(offset);offset+=len(line)
    def pos(n,end=False):
        ln=n.end_lineno if end else n.lineno
        col=n.end_col_offset if end else n.col_offset
        return starts[ln-1]+len(lines[ln-1].encode('utf-8')[:col].decode('utf-8'))
    function=next((n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and pos(n)==scope.start),None)
    if function is None:raise Unsupported('Python 함수 범위를 연결하지 못했습니다.')
    def block(body,depth=0):
        if depth>MAX_DEPTH:raise Unsupported('조건 중첩 깊이 제한')
        out=[]
        for n in body:
            if isinstance(n,ast.If):
                if any(isinstance(t,(ast.Yield,ast.YieldFrom,ast.Lambda,ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp)) for t in ast.walk(n.test)):
                    raise Unsupported(f'조건식의 중첩 실행/지연 평가 · L{n.lineno}')
                out.append(Statement('decision',pos(n.test),pos(n.test,True),block(n.body,depth+1),block(n.orelse,depth+1)))
                continue
            allowed=(ast.Return,ast.Raise,ast.Assign,ast.AnnAssign,ast.AugAssign,ast.Expr,ast.Pass,ast.Import,ast.ImportFrom,ast.Delete)
            if not isinstance(n,allowed):raise Unsupported(f'미지원 Python 문법 {type(n).__name__} · L{n.lineno}')
            if any(isinstance(t,(ast.Yield,ast.YieldFrom,ast.Lambda,ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp)) for t in ast.walk(n)):
                raise Unsupported(f'중첩 실행/지연 평가 표현식 · L{n.lineno}')
            kind='return' if isinstance(n,ast.Return) else 'raise' if isinstance(n,ast.Raise) else 'action'
            out.append(Statement(kind,pos(n),pos(n,True)))
        return out
    return block(function.body)


class LexicalBody:
    """Explicit semicolon statements and if/else only; not a JS/TS/Dart parser.

    Opaque expressions preserve strings/object literals but callback/function
    bodies and unsupported control keywords fail closed. ASI is not inferred.
    """
    def __init__(self,code: str,text: str,scope: Scope):
        self.code=code;self.text=text;self.scope=scope
    def skip(self,i,end):
        while i<end and self.code[i].isspace():i+=1
        return i
    def block(self,start,end,depth=0):
        if depth>MAX_DEPTH:raise Unsupported('조건 중첩 깊이 제한')
        result=[];i=start
        while (i:=self.skip(i,end))<end:
            if self.code[i]==';':i+=1;continue
            stmt,i=self.statement(i,end,depth)
            result.append(stmt)
        return result
    def statement(self,i,end,depth):
        if depth>MAX_DEPTH:raise Unsupported('조건 중첩 깊이 제한')
        code=self.code
        if re.match(r'if\b',code[i:end]):
            par=self.skip(i+2,end)
            if code[par:par+1]!='(':raise Unsupported('if 조건 괄호 미확인')
            close=matching(code,par)
            if close is None or close>=end:raise Unsupported('if 조건 범위 미확인')
            self.expression(par+1,close)
            yes,after=self.branch(self.skip(close+1,end),end,depth+1)
            no=[];tail=self.skip(after,end)
            if re.match(r'else\b',code[tail:end]):
                no,after=self.branch(self.skip(tail+4,end),end,depth+1)
            return Statement('decision',par+1,close,yes,no),after
        if re.match(r'(for|while|try|catch|finally|switch|do|break|continue|yield|function|class|else)\b',code[i:end]):
            raise Unsupported(f'미지원 제어 문법 · L{line_at(self.text,i)}')
        begin=i;kind='action';keyword=re.match(r'(return|throw)\b',code[i:end])
        if keyword:
            kind='return' if keyword.group(1)=='return' else 'raise'
            next_code=self.skip(i+keyword.end(),end)
            if '\n' in code[i+keyword.end():next_code] and not self.scope.path.lower().endswith('.dart'):
                raise Unsupported('return/throw 다음 줄바꿈(ASI) 미지원')
        stack=[]
        while i<end:
            c=code[i]
            if c in '([{':stack.append(c)
            elif c in ')]}':
                expected={')':'(',']':'[','}':'{'}[c]
                if not stack or stack.pop()!=expected:raise Unsupported('문장 괄호 범위 미확인')
            if c in '\r\n' and not stack:
                before=code[begin:i].rstrip();after=self.skip(i+1,end)
                following=code[after:after+1]
                if before and following and before[-1] not in '=,+-*/?:.&|' and following not in '.,()+-*/?:;=' and not before.endswith('await'):
                    raise Unsupported('줄바꿈 사이 명시적 문장 경계/ASI 미확인')
            if c==';' and not stack:
                self.expression(begin,i)
                # Catch missing semicolon followed by a second statement. We do
                # not guess where ASI was intended to split the source.
                tail=code[begin+(keyword.end() if keyword else 0):i]
                if re.search(r'\b(return|throw|if|else|try|for|while|const|let|final|var)\b',tail.lstrip() if keyword else re.sub(r'^(?:const|let|var|final)\b','',tail)):
                    raise Unsupported('한 문장 안의 제어/선언 경계 미확인')
                return Statement(kind,begin,i+1),i+1
            i+=1
        raise Unsupported('명시적 세미콜론 없는 문장/ASI 미지원')
    def expression(self,start,end):
        segment=self.code[start:end]
        if '=>' in segment or re.search(r'\b(function|yield)\b',segment):
            raise Unsupported('중첩 함수/콜백/지연 실행 미지원')
        if '`' in self.text[start:end]:
            raise Unsupported('템플릿 문자열 내 실행 표현식 미지원')
    def branch(self,i,end,depth):
        if i>=end:raise Unsupported('조건 본문 없음')
        if self.code[i]=='{':
            close=matching(self.code,i)
            if close is None or close>=end:raise Unsupported('조건 본문 괄호 불일치')
            return self.block(i+1,close,depth),close+1
        stmt,after=self.statement(i,end,depth)
        return [stmt],after


def build_activity(flow: ProcessFlow,scope: Scope,text: str,masked: tuple[str,str],evidence: Callable,tree=None) -> ActivityFlow:
    parser='python-ast' if scope.parser=='ast' else 'lexical-subset'
    model=ActivityFlow(status='supported-subset',parser=parser,warnings=list(ASSUMPTIONS))
    try:
        if scope.kind=='sdk':raise Unsupported('SDK 호출 조각은 전체 함수 제어 흐름이 아닙니다.')
        if scope.parser=='ast':
            if tree is None:raise Unsupported('Python AST 파싱 실패')
            statements=python_body(text,scope,tree)
        elif masked[1][scope.start:scope.body].rstrip().endswith('=>'):
            LexicalBody(masked[1],text,scope).expression(scope.body,scope.end)
            statements=[Statement('return',scope.body,scope.end)]
        else:
            statements=LexicalBody(masked[1],text,scope).block(scope.body,scope.end)
        def node(kind,start,end,label=None,synthetic=False):
            if len(model.nodes)>=MAX_NODES:raise Unsupported(f'활동 노드 제한 {MAX_NODES}개 초과')
            line=line_at(text,start);last=line_at(text,max(start,end-1))
            eid=evidence(scope,start,end,kind='activity-'+kind)
            steps=[s.id for s in flow.steps if s.line<=last and s.end_line>=line]
            label=label or re.sub(r'\s+',' ',masked[0][start:end]).strip()[:240]
            n=ActivityNode(offset=start,end_offset=end,id=stable_id('activity',flow.id,kind,str(start),str(len(model.nodes))),kind=kind,label=label or '작업',line=line,end_line=last,node_ids=flow.node_ids,evidence_ids=[eid],step_ids=steps,synthetic=synthetic,semantic_status='unknown' if kind=='action' else 'syntax')
            if not synthetic:
                n.call_refs=[ActivityCallRef(step_id=s.id,call_index=i) for s in flow.steps for i,c in enumerate(s.calls) if start<=c.offset<end]
            model.nodes.append(n);return n
        def link(frontier,target):
            by_id={n.id:n for n in model.nodes}
            for source,guard in frontier:
                eids=list(dict.fromkeys(by_id[source].evidence_ids+target.evidence_ids))
                model.edges.append(ActivityEdge(id=stable_id('control',flow.id,source,target.id,guard),source=source,target=target.id,guard=guard,evidence_ids=eids))
        def emit(body,frontier):
            for stmt in body:
                if not frontier:
                    model.warnings.append(f'unreachable: 명시적 종료 뒤 L{line_at(text,stmt.start)} 이후는 연결하지 않았습니다. 소스 순서 보기에는 남아 있습니다.')
                    break
                n=node(stmt.kind,stmt.start,stmt.end)
                link(frontier,n)
                if stmt.kind=='decision':
                    yes=emit(stmt.yes,[(n.id,'true')]);no=emit(stmt.no,[(n.id,'false')])
                    if yes and no:
                        merge=node('merge',stmt.start,stmt.end,'조건 경로 합류',True)
                        link(yes+no,merge);frontier=[(merge.id,'')]
                    else:frontier=yes+no
                elif stmt.kind in {'return','raise'}:
                    final=node('final' if stmt.kind=='return' else 'exception-final',stmt.start,stmt.end,'정상 종료' if stmt.kind=='return' else '예외 전파 종료',True)
                    link([(n.id,'')],final);frontier=[]
                else:frontier=[(n.id,'')]
            return frontier
        initial=node('initial',scope.start,max(scope.start+1,scope.body),'본문 진입',True)
        frontier=emit(statements,[(initial.id,'')])
        if frontier:
            final=node('final',max(scope.body,scope.end-1),scope.end,'본문 끝 · 정상 경로',True)
            link(frontier,final)
    except (Unsupported,RecursionError) as exc:
        return ActivityFlow(status='unsupported',parser=parser,reason=str(exc) or '문법 중첩 한계',warnings=list(ASSUMPTIONS)+['활동 그래프를 만들지 않았습니다. 기존 소스 읽기 순서 보기로 확인하세요.'])
    return model


def attach_activities(result,files,scopes,masked,evidence):
    trees={}
    for path,text in files.items():
        if path.lower().endswith('.py'):
            try:trees[path]=ast.parse(text)
            except (SyntaxError,RecursionError):trees[path]=None
    for flow in result.flows:
        scope=scopes[flow.id]
        flow.activity=build_activity(flow,scope,files[flow.path],masked[flow.path],evidence,trees.get(flow.path))
        ids=[e for n in flow.activity.nodes for e in n.evidence_ids]
        flow.evidence_ids=list(dict.fromkeys(flow.evidence_ids+ids))


def verify_activity(flow: ProcessFlow,registry: dict) -> None:
    """Structural gate, separate from projection; no runtime correctness claim."""
    from .verifier import VerificationError
    a=flow.activity
    if a is None:return  # Backward-compatible saved result.
    def require(ok,message):
        if not ok:raise VerificationError('activity: '+message)
    require(not a.runtime_verified and a.semantics=='explicit-branch-control-flow','runtime/semantics claim')
    if a.status=='unsupported':
        require(bool(a.reason) and not a.nodes and not a.edges,'unsupported body has a fabricated graph')
        return
    nodes={n.id:n for n in a.nodes};edges={e.id:e for e in a.edges}
    require(bool(nodes) and len(nodes)==len(a.nodes) and len(edges)==len(a.edges),'duplicate/empty graph IDs')
    require(len(nodes)<=MAX_NODES,'node budget')
    incoming={i:[] for i in nodes};outgoing={i:[] for i in nodes}
    stepids={s.id for s in flow.steps}
    for n in a.nodes:
        require(flow.line<=n.line<=n.end_line<=flow.end_line,'source range')
        require(bool(n.node_ids) and set(n.node_ids)<=set(flow.node_ids),'file membership')
        require(set(n.step_ids)<=stepids,'step membership')
        require(bool(n.evidence_ids) and set(n.evidence_ids)<=set(flow.evidence_ids),'evidence membership')
        require(all(e in registry and registry[e].path==flow.path and n.line<=registry[e].line<=n.end_line for e in n.evidence_ids),'source evidence')
        for ref in n.call_refs:
            step=next((s for s in flow.steps if s.id==ref.step_id),None)
            require(not n.synthetic and step is not None and ref.step_id in n.step_ids and 0<=ref.call_index<len(step.calls),'call reference')
            require(n.line<=registry[step.calls[ref.call_index].evidence_id].line<=n.end_line and n.offset<=step.calls[ref.call_index].offset<n.end_offset,'call source range')
        require(n.synthetic==(n.kind in {'initial','merge','final','exception-final'}),'synthesized control node flag')
        require(n.semantic_status==('unknown' if n.kind=='action' else 'syntax'),'semantic certainty')
    for e in a.edges:
        require(e.source in nodes and e.target in nodes,'dangling endpoint')
        require(e.relation=='control-flow' and e.confidence=='static-candidate','relation/confidence')
        require(set(e.evidence_ids)==set(nodes[e.source].evidence_ids+nodes[e.target].evidence_ids),'edge provenance')
        require(e.guard in {'true','false'} if nodes[e.source].kind=='decision' else e.guard=='','guard placement')
        outgoing[e.source].append(e);incoming[e.target].append(e)
    initial=[n for n in a.nodes if n.kind=='initial'];require(len(initial)==1,'one entry required')
    for n in a.nodes:
        ins=incoming[n.id];outs=outgoing[n.id]
        if n.kind=='initial':require(not ins and len(outs)==1,'entry degree')
        elif n.kind in {'final','exception-final'}:require(bool(ins) and not outs,'terminal continuation')
        elif n.kind=='decision':require(len(ins)==1 and len(outs)==2 and {e.guard for e in outs}=={'true','false'},'decision guards')
        elif n.kind=='merge':require(len(ins)>=2 and len(outs)==1,'merge degree')
        else:
            require(len(ins)==1 and len(outs)==1,'action degree')
            if n.kind in {'return','raise'}:
                require(nodes[outs[0].target].kind==('final' if n.kind=='return' else 'exception-final'),'abrupt exit continues to action')
    # Supported subset has no loops: Kahn traversal verifies both reachability
    # and acyclicity, rejecting a plausible-looking but corrupt export.
    indegree={i:len(incoming[i]) for i in nodes};todo=[initial[0].id];seen=set()
    while todo:
        i=todo.pop();require(i not in seen,'cycle');seen.add(i)
        for e in outgoing[i]:
            indegree[e.target]-=1
            if indegree[e.target]==0:todo.append(e.target)
    require(seen==set(nodes),'cycle or unreachable node')
