"""Bounded Python HTTP receiver provenance; no imports or target code execution.

Recognizes explicit requests/httpx imports and local Client/Session construction.
Unknown receivers, parameters and reassignments do not become HTTP calls simply
because their name is 'client', 'session' or their method is 'get'. Dynamic
factories, monkey-patching and interprocedural type inference remain unsupported.
"""
from __future__ import annotations
import ast

METHODS = {'get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'request'}
CONSTRUCTORS = {'requests.Session': 'requests', 'httpx.Client': 'httpx',
                'httpx.AsyncClient': 'httpx'}
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def python_http_calls(tree: ast.AST) -> dict[int, str]:
    found: dict[int, str] = {}

    def qual(node: ast.AST, env: dict[str, str]) -> str:
        if isinstance(node, ast.Name):
            return env.get(node.id, '')
        if isinstance(node, ast.Attribute):
            parent = qual(node.value, env)
            return parent + '.' + node.attr if parent else ''
        return ''

    def value(node: ast.AST | None, env: dict[str, str]) -> str:
        if isinstance(node, ast.Call):
            return CONSTRUCTORS.get(qual(node.func, env), '')
        return qual(node, env) if node is not None else ''

    def stores(node: ast.AST) -> set[str]:
        # Used only to invalidate local variables. A nested body has another scope.
        if isinstance(node, (*FUNCTIONS, ast.ClassDef)):
            return {node.name} if hasattr(node, 'name') else set()
        return ({node.id} if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) else set()).union(
            *(stores(child) for child in ast.iter_child_nodes(node)))

    def walk(node: ast.AST, env: dict[str, str]) -> None:
        if isinstance(node, ast.Import):
            for a in node.names:
                env[a.asname or a.name.split('.')[0]] = a.name if a.name in {'httpx', 'requests'} else ''
            return
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                env[a.asname or a.name] = node.module + '.' + a.name if not node.level and node.module in {'requests', 'httpx'} else ''
            return
        if isinstance(node, FUNCTIONS):
            local = env.copy()
            args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            args += [a for a in (node.args.vararg, node.args.kwarg) if a]
            for a in args:
                local[a.arg] = ''
            body = node.body if isinstance(node.body, list) else [node.body]
            for stmt in body:
                for name in stores(stmt):
                    local[name] = ''
            for stmt in body:
                walk(stmt, local)
            if hasattr(node, 'name'):
                env[node.name] = ''
            return
        if isinstance(node, ast.ClassDef):
            local = env.copy()
            for stmt in node.body:
                walk(stmt, local)
            env[node.name] = ''
            return
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            assigned = value(node.value, env)
            if node.value is not None:
                walk(node.value, env)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for name in stores(target):
                    env[name] = assigned if isinstance(target, ast.Name) else ''
            return
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                walk(item.context_expr, env)
                if isinstance(item.optional_vars, ast.Name):
                    env[item.optional_vars.id] = value(item.context_expr, env)
            for stmt in node.body:
                walk(stmt, env)
            return
        if isinstance(node, ast.If):
            walk(node.test, env)
            a, b = env.copy(), env.copy()
            for stmt in node.body: walk(stmt, a)
            for stmt in node.orelse: walk(stmt, b)
            env.update({k: a.get(k, '') if a.get(k) == b.get(k) else '' for k in a.keys() | b.keys()})
            return
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.Try, ast.TryStar)):
            # Loop/exception scopes are not proven control flow. Invalidate writes.
            for name in stores(node): env[name] = ''
            for child in ast.iter_child_nodes(node): walk(child, env.copy())
            return
        if isinstance(node, ast.Call):
            name = qual(node.func, env)
            parts = name.split('.')
            if len(parts) == 2 and parts[0] in {'httpx', 'requests'} and parts[1] in METHODS:
                found[id(node)] = name
        for child in ast.iter_child_nodes(node):
            walk(child, env)

    walk(tree, {})
    return found
