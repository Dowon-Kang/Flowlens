"""Bounded lexical symbol lookup over parsed Python source, never imports it.

This is NOT a compiler/SCIP index. Only explicit imports and unambiguous lexical
function definitions are linked. Rebinding, conditional definitions, parameters,
wildcards, dynamic attributes and re-exports remain unresolved.
"""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
from .graph import resolve_import

FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass
class Binding:
    kind: str
    at: int
    target: str = ''
    member: str = ''
    flow_id: str = ''
    conditional: bool = False


@dataclass
class Environment:
    parent: Environment | None = None
    kind: str = 'module'
    bindings: dict[str, list[Binding]] = field(default_factory=dict)
    wildcard: bool = False

    def bind(self, name: str, binding: Binding) -> None:
        self.bindings.setdefault(name, []).append(binding)


class PythonSymbolIndex:
    def __init__(self, files: dict[str, str], scopes: list):
        self.paths = set(files)
        self.modules: dict[str, Environment] = {}
        self.calls: dict[tuple[str, int], Environment] = {}
        scope_ids = {(s.path, s.start): s.id for s in scopes if s.parser == 'ast'}
        for path, text in files.items():
            if not path.lower().endswith('.py'):
                continue
            try:
                tree = ast.parse(text)
            except (SyntaxError, RecursionError, ValueError):
                continue
            lines = text.splitlines(keepends=True)
            starts = []; offset = 0
            for line in lines:
                starts.append(offset); offset += len(line)

            def pos(node):
                ln = getattr(node, 'lineno', 1)
                col = getattr(node, 'col_offset', 0)
                return starts[ln-1] + len(lines[ln-1].encode('utf-8')[:col].decode('utf-8')) if lines else 0

            def shadow(target, env, at, conditional=False):
                if isinstance(target, ast.Name):
                    env.bind(target.id, Binding('shadowed', at, conditional=conditional))
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for item in target.elts: shadow(item, env, at, conditional)
                elif isinstance(target, ast.Starred): shadow(target.value, env, at, conditional)
                elif isinstance(target, ast.Attribute):
                    # A visible attribute mutation invalidates that receiver too.
                    root = target
                    while isinstance(root, ast.Attribute): root = root.value
                    if isinstance(root, ast.Name): env.bind(root.id, Binding('shadowed', at))

            def scan(node, env, conditional=False):
                at = pos(node)
                if isinstance(node, FUNCTIONS):
                    env.bind(node.name, Binding('function', at, flow_id=scope_ids.get((path, at), ''), conditional=conditional))
                    parent = env.parent if env.kind == 'class' else env
                    local = Environment(parent, 'function')
                    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                    args += [a for a in (node.args.vararg, node.args.kwarg) if a]
                    for a in args: local.bind(a.arg, Binding('parameter', at))
                    for stmt in node.body: scan(stmt, local)
                    return
                if isinstance(node, ast.ClassDef):
                    env.bind(node.name, Binding('shadowed', at))
                    local = Environment(env, 'class')
                    for stmt in node.body: scan(stmt, local)
                    return
                if isinstance(node, ast.Lambda):
                    # The processing scanner does not expand lambda bodies.
                    return
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        env.bind(alias.asname or alias.name.split('.')[0], Binding('module', at,
                            target=alias.name, member='' if alias.asname else alias.name, conditional=conditional))
                    return
                if isinstance(node, ast.ImportFrom):
                    module = '.' * node.level + (node.module or '')
                    for alias in node.names:
                        if alias.name == '*': env.wildcard = True
                        else: env.bind(alias.asname or alias.name, Binding('import', at, target=module, member=alias.name, conditional=conditional))
                    return
                if isinstance(node, (ast.Global, ast.Nonlocal)):
                    for name in node.names: env.bind(name, Binding('dynamic-scope', at))
                    return
                if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
                    binding_env = env
                    if isinstance(node, ast.NamedExpr):
                        # PEP 572: a comprehension's := binds in its containing scope.
                        while binding_env.kind == 'comprehension' and binding_env.parent is not None:
                            binding_env = binding_env.parent
                    for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                        shadow(target, binding_env, at, conditional)
                    if node.value is not None: scan(node.value, env, conditional)
                    return
                if isinstance(node, ast.Delete):
                    for target in node.targets: shadow(target, env, at)
                    return
                if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    local = Environment(env, 'comprehension')
                    for index, gen in enumerate(node.generators):
                        # Only the outermost iterable is evaluated outside the comprehension.
                        scan(gen.iter, env if index == 0 else local, conditional)
                        shadow(gen.target, local, at)
                        for cond in gen.ifs: scan(cond, local, True)
                    for attr in ('elt', 'key', 'value'):
                        if hasattr(node, attr): scan(getattr(node, attr), local, conditional)
                    return
                if isinstance(node, (ast.For, ast.AsyncFor)):
                    shadow(node.target, env, at, True)
                if isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if item.optional_vars: shadow(item.optional_vars, env, at, conditional)
                if isinstance(node, ast.ExceptHandler) and node.name:
                    env.bind(node.name, Binding('shadowed', at))
                if isinstance(node, ast.MatchAs) and node.name:
                    env.bind(node.name, Binding('shadowed', at))
                if isinstance(node, ast.MatchStar) and node.name:
                    env.bind(node.name, Binding('shadowed', at))
                if isinstance(node, ast.MatchMapping) and node.rest:
                    env.bind(node.rest, Binding('shadowed', at))
                if isinstance(node, ast.Call): self.calls[(path, at)] = env
                conditional = conditional or isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.TryStar, ast.Match))
                for child in ast.iter_child_nodes(node): scan(child, env, conditional)

            env = Environment()
            scan(tree, env)
            self.modules[path] = env

    def resolve(self, path: str, at: int, name: str) -> tuple[str, str, str]:
        def unknown(reason): return '', 'unresolved', reason
        env = self.calls.get((path, at))
        if env is None: return unknown('지원 범위 밖의 호출 문법입니다.')
        bits = name.split('.')
        if not all(b.isidentifier() for b in bits): return unknown('동적 수신 객체의 대상을 확인하지 못했습니다.')
        origin = env
        while env is not None:
            if env.wildcard: return unknown('별표 import가 있어 이름의 대상을 확정하지 않습니다.')
            choices = env.bindings.get(bits[0], [])
            if choices:
                if len(choices) != 1: return unknown('같은 이름의 복수 정의·재바인딩이 있어 연결하지 않습니다.')
                binding = choices[0]
                if binding.kind in {'parameter', 'shadowed', 'dynamic-scope'}:
                    return unknown('인자·로컬 변수·동적 스코프가 이름을 가립니다.')
                if binding.conditional: return unknown('조건부 바인딩의 대상을 확정하지 않습니다.')
                if env is origin and binding.at > at: return unknown('호출보다 뒤의 로컬 정의를 실행 대상으로 추정하지 않습니다.')
                if binding.kind == 'function':
                    if len(bits) == 1 and binding.flow_id:
                        return binding.flow_id, 'python-local', '가장 가까운 스코프의 유일한 함수 정의입니다. 실행은 미검증입니다.'
                    return unknown('함수 객체의 동적 속성은 추적하지 않습니다.')
                if binding.kind == 'module' and len(bits) >= 2:
                    expected = binding.member.split('.') if binding.member else [bits[0]]
                    if bits[:-1] != expected:
                        return unknown('명시적으로 가져오지 않은 하위 모듈·동적 속성을 추정하지 않습니다.')
                    target = resolve_import(path, binding.target, self.paths, {})
                    return self._definition(target, bits[-1])
                if binding.kind == 'import':
                    if len(bits) == 1:
                        target = resolve_import(path, binding.target, self.paths, {})
                        return self._definition(target, binding.member)
                    if len(bits) != 2:
                        return unknown('가져온 이름 아래의 추가 모듈·동적 속성을 추정하지 않습니다.')
                    module = binding.target + ('' if binding.target.endswith('.') else '.') + binding.member
                    target = resolve_import(path, module, self.paths, {})
                    return self._definition(target, bits[-1])
                return unknown('명시적 import 또는 함수 정의로 연결하지 못했습니다.')
            env = env.parent
        return unknown('선택된 소스의 스코프에서 호출 대상을 찾지 못했습니다.')

    def _definition(self, path: str | None, name: str) -> tuple[str, str, str]:
        module = self.modules.get(path)
        bindings = module.bindings.get(name, []) if module is not None and not module.wildcard else []
        if len(bindings) == 1:
            b = bindings[0]
            if b.kind == 'function' and b.flow_id and not b.conditional:
                return b.flow_id, 'python-import', '명시적 import와 대상 파일의 유일한 함수 정의를 연결한 정적 후보입니다.'
        return '', 'unresolved', '가져온 모듈의 유일한 함수 정의를 찾지 못했습니다. 누락·재수출·동적 속성은 미확인입니다.'
