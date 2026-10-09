"""Read-only bounded source scopes. No evaluation, imports, or target execution.
Python uses AST ranges; TS/JS/Dart use masked balanced delimiters. Source order,
not a CFG: callbacks, exceptions, loops and dynamic dispatch remain uncertain.
"""
from __future__ import annotations
import ast
import io
import tokenize
import re
from dataclasses import dataclass, field
from .extractor import masks, stable_id

@dataclass
class Scope:
    id: str
    path: str
    name: str
    start: int
    body: int
    end: int
    kind: str = 'function'
    endpoint: str = ''
    method: str = ''
    parser: str = 'lexical'
    statements: list[tuple[int,int]] = field(default_factory=list)
    calls: list[tuple[int,str]] = field(default_factory=list)
    class_name: str = ''
    parameters: set[str] = field(default_factory=set)


def source_masks(path: str, text: str) -> tuple[str,str]:
    if not path.lower().endswith('.py'):return masks(text)
    lines=text.splitlines(keepends=True);starts=[0]
    for line in lines:starts.append(starts[-1]+len(line))
    nc=list(text);code=list(text)
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type not in {tokenize.COMMENT,tokenize.STRING}:continue
            start=starts[token.start[0]-1]+token.start[1];end=starts[token.end[0]-1]+token.end[1]
            for i in range(start,end):
                if text[i] not in '\r\n':
                    code[i]=' '
                    if token.type==tokenize.COMMENT:nc[i]=' '
    except (tokenize.TokenError,IndentationError):pass
    return ''.join(nc),''.join(code)


def matching(code: str, start: int) -> int | None:
    pairs={'(':')','{':'}','[':']'}
    if start>=len(code) or code[start] not in pairs:return None
    stack=[pairs[code[start]]]
    for i in range(start+1,len(code)):
        c=code[i]
        if c in pairs:stack.append(pairs[c])
        elif c in ')}]':
            if not stack or c!=stack[-1]:return None
            stack.pop()
            if not stack:return i
    return None


def line_at(text: str, offset: int) -> int:
    return text.count('\n',0,offset)+1


def statement_ranges(code: str, start: int, end: int) -> list[tuple[int,int]]:
    """Top-level statements; conditional blocks remain ONE scoped operation."""
    ranges=[];i=start
    while i<end:
        while i<end and (code[i].isspace() or code[i]==';'):i+=1
        if i>=end:break
        begin=i;stack=[];block=bool(re.match(r'(if|for|while|try|switch|do)\b',code[i:]))
        while i<end:
            c=code[i]
            if c in '([{':stack.append(c)
            elif c in ')]}':
                if stack:stack.pop()
                if block and c=='}' and not stack:
                    tail=re.match(r'\s*(else\b|catch\b|finally\b)',code[i+1:end])
                    if not tail:i+=1;break
            if c==';' and not stack:i+=1;break
            i+=1
        if i>begin:ranges.append((begin,i))
    return ranges


def _body_after(code: str, close: int, limit: int) -> tuple[int,int] | None:
    """Skip optional TS return type, including a balanced object return type."""
    tail=code[close+1:limit];m=re.search(r'=>|\{|;',tail)
    if not m:return None
    at=close+1+m.start()
    if m.group()==';':return None
    if m.group()=='=>':
        at+=2
        while at<limit and code[at].isspace():at+=1
        if at<limit and code[at]=='{':
            end=matching(code,at);return (at+1,end) if end is not None else None
        end=code.find(';',at,limit)
        return (at,end if end>=0 else limit)
    end=matching(code,at)
    if end is None:return None
    rest=re.match(r'\s*\{',code[end+1:limit])
    # `): {a: number} { ... }` has a type literal before its actual body.
    if ':' in code[close+1:at] and rest:
        at=end+1+rest.end()-1;end=matching(code,at)
    return (at+1,end) if end is not None else None


def lexical_scopes(path: str, text: str, facts: list) -> list[Scope]:
    nc,code=masks(text);scopes=[];seen=set()
    classes=[]
    for m in re.finditer(r'\bclass\s+(\w+)[^{;]*\{',code):
        b=m.end()-1;e=matching(code,b)
        if e is not None:classes.append((m.group(1),b,e))
    for f in facts:
        if f.kind!='symbol':continue
        # Find declaration, not a later call sharing the same name.
        patterns=[r'\bfunction\s+'+re.escape(f.value)+r'\s*\(',
                  r'\b(?:const|let)\s+'+re.escape(f.value)+r'\s*=\s*(?:async\s*)?\(',
                  r'\b(?:Future<[^;\n]+?>|void|String|Widget|dynamic|int|bool)\s+'+re.escape(f.value)+r'\s*\(']
        for pattern in patterns:
            for m in re.finditer(pattern,code):
                if m.start() in seen:continue
                par=m.end()-1;close=matching(code,par)
                if close is None:continue
                body=_body_after(code,close,min(len(code),close+16000))
                if not body:continue
                b,e=body
                if e-b>65536:continue
                owner=next((name for name,cb,ce in reversed(classes) if cb<m.start()<ce),'')
                params=set(re.findall(r'(?<![\w])([A-Za-z_$]\w*)\s*(?=[:,=)]|$)',code[par+1:close]))
                s=Scope(stable_id('flow',path,str(m.start())),path,f.value,m.start(),b,e,class_name=owner,parameters=params)
                scopes.append(s);seen.add(m.start())
    # Class methods, including multiline typed parameters (not constructors).
    for owner,cb,ce in classes:
        pat=r'(?:^|\n)\s*(?:(?:public|private|protected|static|async|override)\s+)*([A-Za-z_$]\w*)\s*\('
        for m in re.finditer(pat,code[cb+1:ce]):
            start=cb+1+m.start();name=m.group(1)
            if name in {'if','for','while','switch','catch','constructor'}:continue
            if any(s.start<=start<s.end for s in scopes):continue
            par=cb+1+m.end()-1;close=matching(code,par)
            if close is None:continue
            body=_body_after(code,close,ce)
            if body:scopes.append(Scope(stable_id('flow',path,str(start)),path,name,start,*body,class_name=owner))
    route_pattern=r'\b([\w$]+)\.(get|post|put|patch|delete|head|options)\s*\(\s*[\'\"]([^\'\"\n]+)[\'\"]'
    for m in re.finditer(route_pattern,nc):
        if not code[m.start():m.start()+3].strip():continue
        if not any(f.kind=='route' and f.value==m.group(3) and f.method==m.group(2).upper() for f in facts):continue
        par=nc.find('(',m.start());close=matching(code,par)
        if close is None:continue
        arrow=code.find('=>',m.end(),close)
        if arrow<0:continue  # Named handler references are not silently fabricated.
        b=arrow+2
        while b<close and code[b].isspace():b+=1
        if code[b:b+1]=='{':
            e=matching(code,b)
            if e is None:continue
            b+=1
        else:e=close
        scopes.append(Scope(stable_id('flow',path,str(m.start())),path,f'{m.group(2).upper()} {m.group(3)}',m.start(),b,e,'route',m.group(3),m.group(2).upper()))
    for s in scopes:
        s.statements=statement_ranges(code,s.body,s.end)
        children=[t for t in scopes if s.body<=t.start<s.end and t.id!=s.id]
        for m in re.finditer(r'(?<![.\w$])([A-Za-z_$][\w$]*(?:\??\.[A-Za-z_$][\w$]*)*)\s*(?:<[^;()]{1,160}>)?\s*\(',code[s.body:s.end]):
            at=s.body+m.start();name=m.group(1)
            if name in {'if','for','while','switch','catch','function'}:continue
            if any(t.start<=at<=t.end for t in children):continue
            s.calls.append((at,name))
        for m in re.finditer(r'\bnew\s+(\w+)\s*\(',code[s.body:s.end]):
            at=s.body+m.start();par=s.body+m.end()-1;close=matching(code,par)
            if close is None:continue
            method=re.match(r'\s*\.\s*(\w+)\s*\(',code[close+1:s.end])
            if method:s.calls.append((at,'new:'+m.group(1)+'.'+method.group(1)))
        s.calls.sort()
    return scopes


def python_scopes(path: str,text: str,facts: list) -> list[Scope]:
    try:tree=ast.parse(text)
    except (SyntaxError,RecursionError):return []
    lines=text.splitlines(keepends=True);starts=[];offset=0
    for line in lines:starts.append(offset);offset+=len(line)
    def pos(node,end=False):
        ln=getattr(node,'end_lineno' if end else 'lineno');col=getattr(node,'end_col_offset' if end else 'col_offset')
        return starts[ln-1]+len(lines[ln-1].encode()[:col].decode('utf-8'))
    scopes=[]
    def walk(node,cls=''):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            s=Scope(stable_id('flow',path,str(pos(node))),path,node.name,pos(node),pos(node.body[0]),pos(node,True),parser='ast',class_name=cls,parameters={a.arg for a in [*node.args.posonlyargs,*node.args.args,*node.args.kwonlyargs]})
            for d in node.decorator_list:
                if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.args and isinstance(d.args[0],ast.Constant) and isinstance(d.args[0].value,str):
                    if any(f.kind=='route' and f.value==d.args[0].value and f.method==d.func.attr.upper() for f in facts):
                        s.kind='route';s.endpoint=d.args[0].value;s.method=d.func.attr.upper();s.name=f'{s.method} {s.endpoint}'
            s.statements=[(pos(n),pos(n,True)) for n in node.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
            def calls(n):
                if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda)):return
                if isinstance(n,ast.Call):s.calls.append((pos(n),ast.unparse(n.func)))
                for child in ast.iter_child_nodes(n):calls(child)
            for n in node.body:calls(n)
            s.calls.sort();scopes.append(s)
        for child in ast.iter_child_nodes(node):walk(child,node.name if isinstance(node,ast.ClassDef) else cls)
    walk(tree)
    return scopes
