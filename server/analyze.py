"""Static analysis of the user's source to guide the visualizer."""
from __future__ import annotations

import ast
from collections import defaultdict


def _names(node) -> list[str]:
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id not in out:
            out.append(n.id)
    return out


def code_meta(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {}

    index_vars: dict[str, list[str]] = defaultdict(list)
    roles: dict[str, str] = {}
    funcs: list[str] = []
    recursive: list[str] = []
    compare_lines: set[int] = set()
    loops: list[dict] = []
    heap_funcs = {"heappush", "heappop", "heapify", "heappushpop", "heapreplace"}

    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript):
            base = n.value
            while isinstance(base, ast.Subscript):
                base = base.value
            if isinstance(base, ast.Name):
                for nm in _names(n.slice):
                    if nm not in index_vars[base.id] and nm != base.id:
                        index_vars[base.id].append(nm)
            # nested: also collect inner subscripts' names for the base
            inner = n.value
            while isinstance(inner, ast.Subscript):
                if isinstance(base, ast.Name):
                    for nm in _names(inner.slice):
                        if nm not in index_vars[base.id] and nm != base.id:
                            index_vars[base.id].append(nm)
                inner = inner.value
        elif isinstance(n, ast.Compare):
            compare_lines.add(n.lineno)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(n.name)
            for c in ast.walk(n):
                if isinstance(c, ast.Call):
                    f = c.func
                    if (isinstance(f, ast.Name) and f.id == n.name) or (
                            isinstance(f, ast.Attribute) and f.attr == n.name):
                        if n.name not in recursive:
                            recursive.append(n.name)
        elif isinstance(n, ast.Call):
            f = n.func
            fname = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
            if fname in heap_funcs and n.args and isinstance(n.args[0], ast.Name):
                roles[n.args[0].id] = "heap"
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                var = f.value.id
                if roles.get(var) == "heap":
                    continue
                if f.attr == "popleft" or (f.attr == "pop" and n.args and isinstance(n.args[0], ast.Constant)
                                           and n.args[0].value == 0) or f.attr == "appendleft":
                    roles[var] = "queue"
                elif f.attr == "pop" and not n.args and roles.get(var) != "queue":
                    roles[var] = "stack"
        elif isinstance(n, ast.While):
            loops.append({"line": n.lineno, "end": n.end_lineno, "kind": "while",
                          "names": _names(n.test), "cond": ast.unparse(n.test)})
        elif isinstance(n, ast.For):
            loops.append({"line": n.lineno, "end": n.end_lineno, "kind": "for",
                          "names": _names(n.target) + _names(n.iter),
                          "cond": f"{ast.unparse(n.target)} in {ast.unparse(n.iter)}"})

    # name assignment from deque(...) -> queue unless used as stack
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
            f = n.value.func
            fname = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
            if fname == "deque":
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id not in roles:
                        roles[t.id] = "queue"

    return {
        "index_vars": dict(index_vars),
        "roles": roles,
        "funcs": funcs,
        "recursive": recursive,
        "compare_lines": sorted(compare_lines),
        "loops": loops,
    }
