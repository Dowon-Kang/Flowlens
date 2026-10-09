"""Static facts only. Python AST; conservative lexical JS/TS/Dart adapter."""
from __future__ import annotations
import ast
import hashlib
import re
from pathlib import PurePosixPath
from urllib.parse import quote
from .models import Snapshot, Evidence, Fact
from .intake import SOURCE_SUFFIXES
from .http_clients import python_http_calls

METHODS = {'get', 'post', 'put', 'patch', 'delete', 'options', 'head'}

def stable_id(prefix: str, *parts: str) -> str:
    return prefix + '-' + hashlib.sha256('\x00'.join(parts).encode()).hexdigest()[:14]

def masks(text: str) -> tuple[str, str]:
    """Preserve source offsets/newlines while masking comments and quoted content.
    This is deliberately not a JS/TS/Dart grammar. Template interpolation is ignored.
    """
    comments = list(text)
    code = list(text)
    i = 0
    def blank(start: int, end: int, both: bool):
        for n in range(start, end):
            if text[n] not in '\n\r':
                code[n] = ' '
                if both:
                    comments[n] = ' '
    while i < len(text):
        if text.startswith('//', i):
            j = text.find('\n', i)
            j = len(text) if j < 0 else j
            blank(i, j, True); i = j
        elif text.startswith('/*', i):
            j = text.find('*/', i+2)
            j = len(text) if j < 0 else j+2
            blank(i, j, True); i = j
        elif text[i] == '/' and (
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
        elif text[i] in "'\"`":
            q = text[i]; j = i+1
            while j < len(text):
                if text[j] == '\\': j += 2; continue
                if text[j] == q: j += 1; break
                j += 1
            blank(i, min(j, len(text)), False); i = j
        else:
            i += 1
    return ''.join(comments), ''.join(code)

def lexical_http_candidate(name: str, nc: str, code: str, at: int) -> bool:
    """Restricted SDK/receiver evidence; never proves a live request or origin.

    Used by both request facts and processing labels, so those views cannot
    disagree just because one looked only at a method name.
    """
    owner, _, method = name.rpartition('.')
    if name == 'fetch':
        if at and code[at-1:at] == '.':
            return False
        return not re.search(r'\b(?:function|const|let|var)\s+fetch\b|\([^)]*\bfetch\b[^)]*\)\s*=>', code)
    if method not in METHODS or not re.fullmatch(r'[\w$]+', owner):
        return False
    bindings = {}
    for m in re.finditer(r'\bimport\s+(\w+)\s+from\s*[\'"](axios)[\'"]', nc):
        if code[m.start():m.start()+6] == 'import':
            bindings[m.group(1)] = m.group(2)
    for m in re.finditer(r'\b(?:const|let|var)\s+(\w+)\s*=\s*require\([\'"](axios)[\'"]\)', nc):
        if code[m.start():m.start()+3].strip():
            bindings[m.group(1)] = m.group(2)
    known = owner in bindings
    if re.search(r"\bimport\s*['\"]package:dio/[^'\"]+['\"]", nc):
        # Preserve the existing imported Dio lexical adapter. Missing DI/type
        # origins remain explicitly candidate, not a resolved concrete instance.
        known |= owner.strip('_') == 'dio' or bool(re.search(r'\bDio\s+'+re.escape(owner)+r'\b', code))
    if re.search(r"\bimport\s*['\"]package:http/[^'\"]+['\"]\s+as\s+"+re.escape(owner)+r'\b', nc):
        known = True
    declarations = list(re.finditer(r'\b(?:const|let|var|final)\s+'+re.escape(owner)+r'(?:\s*:[^=;]+)?\s*=(?!=)\s*([^;\n]+)', code[:at]))
    if declarations:
        rhs = declarations[-1].group(1).strip()
        # A visible non-client assignment invalidates even an imported name.
        known = any(re.match(re.escape(alias)+r'\.create\s*\(', rhs) for alias in bindings)
        known |= bool(re.match(r'(?:new\s+)?Dio\s*\(', rhs) and 'package:dio/' in nc)
        if re.match(r'require\s*\(', rhs) and owner in bindings:
            known = True
    return bool(known)


def extract_facts(snapshot: Snapshot) -> tuple[list[Fact], list[Evidence], list[str]]:
    facts: list[Fact] = []
    evidence: dict[str, Evidence] = {}
    warnings: list[str] = []
    def add(path: str, text: str, line: int, kind: str, value: str, parser: str, method: str = '', target: str = '', end_line: int | None = None):
        lines = text.splitlines()
        end = min(end_line or line, len(lines))
        if not lines or not (1 <= line <= end): return
        # Limit source disclosure to a precise short excerpt, preserving exact text.
        end = min(end, line+3)
        eid = stable_id('ev', path, str(line), str(end), kind, value, method)
        url = f'{snapshot.repository_url}/blob/{snapshot.revision}/{quote(path, safe="/")}#L{line}-L{end}' if snapshot.repository_url else ''
        evidence[eid] = Evidence(id=eid, path=path, line=line, end_line=end,
                                snippet='\n'.join(lines[line-1:end]), kind=kind, parser=parser, url=url)
        facts.append(Fact(path=path, kind=kind, value=value, evidence_id=eid, method=method, target=target))

    for file in snapshot.files:
        path, text = file.path, file.content
        suffix = PurePosixPath(path).suffix.lower()
        if suffix not in SOURCE_SUFFIXES: continue
        if suffix == '.py':
            try:
                tree = ast.parse(text)
            except (SyntaxError, RecursionError):
                warnings.append(f'Python 구문을 해석하지 못했습니다: {path}')
                continue
            http_calls = python_http_calls(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        add(path, text, node.lineno, 'import', alias.name, 'ast')
                elif isinstance(node, ast.ImportFrom):
                    module = '.' * node.level + (node.module or '')
                    add(path, text, node.lineno, 'import', module, 'ast')
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    add(path, text, node.lineno, 'symbol', node.name, 'ast')
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for d in node.decorator_list:
                            if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr.lower() in METHODS and d.args and isinstance(d.args[0], ast.Constant) and isinstance(d.args[0].value, str):
                                add(path, text, d.lineno, 'route', d.args[0].value, 'ast', d.func.attr.upper())
                elif isinstance(node, ast.Call):
                    name = http_calls.get(id(node), '')
                    method = name.rsplit('.', 1)[-1]
                    url = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == 'url'), None)
                    if method in METHODS and isinstance(url, ast.Constant) and isinstance(url.value, str):
                        add(path, text, node.lineno, 'request', url.value, 'ast', method.upper(), target=name)
            continue
        nc, code = masks(text)
        def matches(pattern: str):
            for match in re.finditer(pattern, nc, re.M):
                if any(not c.isspace() for c in code[match.start():match.start()+min(6, len(match.group()))]):
                    yield match
        import_patterns = [r'\b(?:import|export)\s+[^;]{1,3000}?\bfrom\s*[\'"]([^\'"\n]+)[\'"]',
                           r'\bimport\s*[\'"]([^\'"\n]+)[\'"]',
                           r'\brequire\s*\(\s*[\'"]([^\'"\n]+)[\'"]\s*\)']
        for pattern in import_patterns:
            for m in matches(pattern):
                add(path,text,text.count('\n',0,m.start())+1,'import',m.group(1),'lexical',end_line=text.count('\n',0,m.end())+1)
        route_pattern = r'\b([A-Za-z_$][\w$]*)\.(get|post|put|patch|delete|options|head)\s*(?:<[^;()]{1,200}>)?\s*\(\s*[\'"]([^\'"\n]+)[\'"]'
        for m in matches(route_pattern):
            obj, method, value = m.groups()
            if '$' in value or '{' in value and not value.startswith('/'):
                continue
            is_client = lexical_http_candidate(obj+'.'+method, nc, code, m.start())
            is_route = obj.lower() in {'app', 'router', 'api', 'server'} or 'route' in obj.lower()
            if is_client or is_route:
                add(path,text,text.count('\n',0,m.start())+1,'request' if is_client else 'route',value,'lexical',method.upper(),end_line=text.count('\n',0,m.end())+1)
        for m in matches(r'\bfetch\s*\(\s*[\'"]([^\'"\n]+)[\'"]'):
            if not lexical_http_candidate('fetch', nc, code, m.start()):
                continue
            # Only a no-options call has an unambiguous default method in this adapter.
            tail = nc[m.end():m.end()+12]
            method = 'GET' if re.match(r'\s*\)', tail) else 'UNKNOWN'
            add(path,text,text.count('\n',0,m.start())+1,'request',m.group(1),'lexical',method)
        for m in matches(r"\b(?:baseUrl|baseURL|base_url)\s*=\s*['\"](https?://[^'\"\n]+)['\"]"):
            add(path,text,text.count('\n',0,m.start())+1,'config-url',m.group(1),'lexical')
        symbols = [r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(',
                   r'\bclass\s+([A-Za-z_$][\w$]*)',
                   r'\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?\([^\n;]*?\)\s*=>']
        if suffix == '.dart':
            symbols += [r'\b(?:Future<[^;\n]+?>|void|String|Widget|dynamic|int|bool)\s+([A-Za-z_$][\w$]*)\s*\(']
        for pattern in symbols:
            for m in matches(pattern):
                add(path,text,text.count('\n',0,m.start())+1,'symbol',m.group(1),'lexical')
    if any(PurePosixPath(f.path).suffix.lower() in SOURCE_SUFFIXES- {'.py'} for f in snapshot.files):
        warnings.append('JS/TS/Dart는 제한된 정적 패턴 분석입니다. 동적 호출, alias, 재수출, 라우트 prefix 조합, 실제 런타임 순서는 완전히 추적하지 않습니다.')
    return facts, list(evidence.values()), warnings
