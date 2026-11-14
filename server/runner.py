"""Child process: executes user code under sys.settrace and dumps a JSON trace.

Run as:  python -E -s runner.py  < {"code": ..., "stdin": ...}
Writes one JSON object to the real stdout.

Each recorded step is a snapshot of the program *before* the line runs
(for "line" events), or at call / return / exception boundaries.
"""
from __future__ import annotations

import ast
import collections
import io
import json
import math
import sys
import time
import types

FILENAME = "<user>"
MAX_STEPS = 3000
MAX_SECONDS = 4.0
MAX_ITEMS = 80
MAX_HEAP = 400
MAX_STR = 200
MAX_STDOUT = 100_000
RECURSION_HEADROOM = 150


class StepLimit(BaseException):
    """Raised from the tracer when the program runs too many steps."""


class TimeLimit(BaseException):
    pass


# ---------------------------------------------------------------- encoding

def _prim(v):
    if v is None:
        return {"t": "none"}
    if isinstance(v, bool):
        return {"t": "bool", "v": v}
    if isinstance(v, int):
        if abs(v) > 2**53:
            return {"t": "int", "v": str(v), "big": True}
        return {"t": "int", "v": v}
    if isinstance(v, float):
        if math.isfinite(v):
            return {"t": "float", "v": v}
        return {"t": "float", "v": repr(v), "special": True}
    if isinstance(v, str):
        if len(v) > MAX_STR:
            return {"t": "str", "v": v[:MAX_STR], "cut": True}
        return {"t": "str", "v": v}
    return None


def _is_user_obj(v) -> bool:
    t = type(v)
    return getattr(t, "__module__", None) == "__main__" and not isinstance(v, type)


class Encoder:
    def __init__(self):
        self.heap: dict[str, dict] = {}

    def enc(self, v):
        p = _prim(v)
        if p is not None:
            return p
        if isinstance(v, (types.FunctionType, types.BuiltinFunctionType, types.MethodType)):
            return {"t": "func", "v": getattr(v, "__name__", "?")}
        if isinstance(v, (type, types.ModuleType)):
            return {"t": "repr", "v": repr(v)[:MAX_STR]}

        oid = str(id(v))
        ref = {"t": "ref", "r": oid}
        if oid in self.heap:
            return ref
        if len(self.heap) >= MAX_HEAP:
            return {"t": "repr", "v": "…"}
        self.heap[oid] = {}  # placeholder (handles cycles)

        if isinstance(v, (list, tuple, collections.deque)):
            kind = "list" if isinstance(v, list) else "tuple" if isinstance(v, tuple) else "deque"
            items = list(v)
            obj = {"t": kind, "items": [self.enc(x) for x in items[:MAX_ITEMS]]}
            if len(items) > MAX_ITEMS:
                obj["more"] = len(items) - MAX_ITEMS
        elif isinstance(v, (set, frozenset)):
            items = list(v)
            try:
                items.sort()
            except TypeError:
                items.sort(key=repr)
            obj = {"t": "set", "items": [self.enc(x) for x in items[:MAX_ITEMS]]}
            if len(items) > MAX_ITEMS:
                obj["more"] = len(items) - MAX_ITEMS
        elif isinstance(v, dict):
            entries = list(v.items())
            obj = {
                "t": "dict",
                "entries": [[self.enc(k), self.enc(x)] for k, x in entries[:MAX_ITEMS]],
            }
            if isinstance(v, collections.defaultdict):
                obj["default"] = True
            if len(entries) > MAX_ITEMS:
                obj["more"] = len(entries) - MAX_ITEMS
        elif _is_user_obj(v):
            fields = {}
            d = getattr(v, "__dict__", None)
            if d is not None:
                for k, x in list(d.items())[:MAX_ITEMS]:
                    fields[k] = self.enc(x)
            for k in getattr(type(v), "__slots__", ()):
                if hasattr(v, k):
                    fields[k] = self.enc(getattr(v, k))
            obj = {"t": "obj", "cls": type(v).__name__, "fields": fields}
        else:
            try:
                r = repr(v)
            except Exception:
                r = f"<{type(v).__name__}>"
            del self.heap[oid]
            return {"t": "repr", "v": r[:MAX_STR], "cls": type(v).__name__}
        self.heap[oid] = obj
        return ref


def _visible_global(name, v) -> bool:
    if name.startswith("__"):
        return False
    if isinstance(v, (types.ModuleType, type, types.FunctionType,
                      types.BuiltinFunctionType, types.MethodType)):
        return False
    return True


# ---------------------------------------------------------------- AST helpers

_SAFE_FUNCS = {"len": len, "min": min, "max": max, "abs": abs}


def _safe_expr(node) -> bool:
    for n in ast.walk(node):
        if isinstance(n, (ast.Name, ast.Constant, ast.BinOp, ast.UnaryOp, ast.Load,
                          ast.operator, ast.unaryop, ast.Attribute, ast.Tuple)):
            continue
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _SAFE_FUNCS \
                and not n.keywords:
            continue
        return False
    return True


def _subscript_chain(node):
    """a[i][j] -> ("a", [i_node, j_node]) or None."""
    idx = []
    while isinstance(node, ast.Subscript):
        if isinstance(node.slice, ast.Slice):
            return None
        idx.append(node.slice)
        node = node.value
    if isinstance(node, ast.Name):
        return node.id, list(reversed(idx))
    return None


def build_line_index(tree):
    """line -> list of (var, [compiled index exprs], [expr texts], in_compare)."""
    by_line: dict[int, list] = collections.defaultdict(list)
    compare_spans: list[ast.Compare] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            compare_spans.append(n)
    seen = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Subscript):
            continue
        ch = _subscript_chain(n)
        if not ch:
            continue
        var, idx_nodes = ch
        if not all(_safe_expr(i) for i in idx_nodes):
            continue
        key = (n.lineno, ast.unparse(n))
        if key in seen:
            continue
        seen.add(key)
        in_cmp = any(
            c.lineno <= n.lineno <= (c.end_lineno or c.lineno)
            and any(sub is n for sub in ast.walk(c))
            for c in compare_spans
        )
        compiled = [compile(ast.Expression(body=i), FILENAME + "-idx", "eval") for i in idx_nodes]
        texts = [ast.unparse(i) for i in idx_nodes]
        by_line[n.lineno].append((var, compiled, texts, in_cmp, ast.unparse(n)))
    # drop inner subscripts of chains (a[i] inside a[i][j]) — keep the longest per text prefix
    for line, items in by_line.items():
        full = [it for it in items if not any(
            other is not it and other[4].startswith(it[4] + "[") for other in items)]
        by_line[line] = full
    return by_line


# ---------------------------------------------------------------- tracer

class Tracer:
    def __init__(self, code_obj, line_index, out_buf, ns=None):
        self.code_obj = code_obj
        self.ns = ns  # set in "driver" mode: the user's functions are called from untraced code
        self.line_index = line_index
        self.out = out_buf
        self.steps: list[dict] = []
        self.start = time.monotonic()
        self.base_depth = 0
        self.exc_ids: list[int | None] = []

    # -- snapshot
    def frames_of(self, frame):
        chain = []
        f = frame
        while f is not None:
            if f.f_code.co_filename == FILENAME:
                chain.append(f)
            f = f.f_back
        chain.reverse()
        return chain

    def fid(self, f):
        if self.ns is not None and f.f_code.co_name == "<module>":
            return "global"
        return str(id(f))

    def snapshot(self, frame, event, arg):
        enc = Encoder()
        frames = []
        chain = self.frames_of(frame)
        if self.ns is not None and (not chain or chain[0].f_code.co_name != "<module>"):
            # called from the driver: there is no module frame on the stack, so show the globals anyway
            frames.append({
                "fn": "global", "fid": "global", "line": 0,
                "vars": {k: enc.enc(v) for k, v in list(self.ns.items()) if _visible_global(k, v)},
            })
        for f in chain:
            is_mod = f.f_code.co_name == "<module>"
            src = f.f_globals if is_mod else f.f_locals
            vars_ = {}
            for k, v in list(src.items()):
                if is_mod and not _visible_global(k, v):
                    continue
                if not is_mod and isinstance(v, (types.ModuleType, type)):
                    continue
                vars_[k] = enc.enc(v)
            frames.append({
                "fn": "global" if is_mod else f.f_code.co_name,
                "fid": self.fid(f),
                "line": f.f_lineno,
                "vars": vars_,
            })
        step = {
            "ev": event,
            "line": frame.f_lineno,
            "fn": frames[-1]["fn"] if frames else "global",
            "fid": self.fid(frame),
            "frames": frames,
            "out": self.out.tell(),
        }
        if event == "return":
            step["ret"] = enc.enc(arg)
        elif event == "exception":
            et, ev, _tb = arg
            step["exc"] = {"type": et.__name__, "msg": str(ev)[:300]}
        if event == "line":
            acc = self.accesses(frame, enc)
            if acc:
                step["acc"] = acc
        step["heap"] = enc.heap
        return step

    def accesses(self, frame, enc):
        items = self.line_index.get(frame.f_lineno)
        if not items:
            return None
        env = dict(frame.f_globals)
        env.update(frame.f_locals)
        env["__builtins__"] = _SAFE_FUNCS
        res = []
        for var, compiled, texts, in_cmp, full in items:
            if var not in env:
                continue
            try:
                idx = [eval(c, env) for c in compiled]  # noqa: S307 - restricted exprs
            except BaseException:
                continue
            container = env[var]
            entry = {"var": var, "idx": [enc.enc(i) for i in idx], "expr": texts,
                     "text": full, "cmp": in_cmp}
            # does the access fall outside the container?
            try:
                c = container
                for i in idx:
                    c = c[i]
                entry["ok"] = True
            except (IndexError, KeyError, TypeError):
                entry["ok"] = False
            except BaseException:
                pass
            res.append(entry)
        return res

    # -- trace callbacks
    def check_limits(self):
        if len(self.steps) >= MAX_STEPS:
            raise StepLimit()
        if time.monotonic() - self.start > MAX_SECONDS:
            raise TimeLimit()

    def trace(self, frame, event, arg):
        if frame.f_code.co_filename != FILENAME:
            return None
        if frame.f_code.co_name != "<module>":  # the module "call" is just noise
            self.record(frame, event, arg)
        return self.local_trace

    def local_trace(self, frame, event, arg):
        if self.ns is not None and event == "return" and frame.f_code.co_name == "<module>":
            return self.local_trace  # the harness runs next; the program isn't over yet
        if event in ("line", "return", "exception"):
            self.record(frame, event, arg)
        return self.local_trace

    def record(self, frame, event, arg):
        if event == "exception" and arg[0] in (StepLimit, TimeLimit):
            return
        self.check_limits()
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(old + 5000)  # encoding deep structures needs room
        try:
            step = self.snapshot(frame, event, arg)
        finally:
            sys.setrecursionlimit(old)
        self.steps.append(step)
        self.exc_ids.append(id(arg[1]) if event == "exception" else None)


def main():
    req = json.loads(sys.stdin.read())
    code = req.get("code", "")
    real_stdout = sys.stdout
    result: dict = {"steps": [], "stdout": "", "error": None}

    try:
        tree = ast.parse(code, FILENAME)
        code_obj = compile(tree, FILENAME, "exec")
    except SyntaxError as e:
        result["error"] = {
            "type": type(e).__name__,
            "msg": e.msg,
            "line": e.lineno or 1,
            "col": e.offset or 1,
            "end_col": getattr(e, "end_offset", None),
            "text": (e.text or "").rstrip("\n"),
        }
        real_stdout.write(json.dumps(result))
        return

    # optional harness around the user's code (problem mode): both run untraced
    prelude = req.get("prelude")
    driver = req.get("driver")
    prelude_obj = compile(prelude, "<prelude>", "exec") if prelude else None
    driver_obj = compile(driver, "<driver>", "exec") if driver else None

    line_index = build_line_index(tree)
    out = io.StringIO()
    ns = {"__name__": "__main__", "__builtins__": __builtins__}
    tracer = Tracer(code_obj, line_index, out, ns if driver_obj else None)

    sys.stdin = io.StringIO(req.get("stdin", "") or "")
    sys.stdout = out
    depth = len(_stack_depth())
    sys.setrecursionlimit(depth + RECURSION_HEADROOM)
    error = None
    try:
        if prelude_obj:
            exec(prelude_obj, ns)
        sys.settrace(tracer.trace)
        exec(code_obj, ns)
        if driver_obj:
            exec(driver_obj, ns)
    except StepLimit:
        error = {"type": "StepLimit", "msg": f"Program ran more than {MAX_STEPS} steps"}
    except TimeLimit:
        error = {"type": "TimeLimit", "msg": f"Program ran longer than {MAX_SECONDS:.0f}s"}
    except BaseException as e:  # user error
        sys.settrace(None)
        tb = e.__traceback__
        line = None
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == FILENAME:
                line = tb.tb_lineno
            tb = tb.tb_next
        error = {"type": type(e).__name__, "msg": str(e)[:500], "line": line}
        if line is None and driver_obj:
            error["driver"] = True  # raised by the call itself (e.g. wrong number of arguments)
        # first step where this exception object was raised
        for i, x in enumerate(tracer.exc_ids):
            if x == id(e):
                error["step"] = i
                break
    finally:
        sys.settrace(None)
        sys.stdout = real_stdout
        sys.setrecursionlimit(10_000)

    if error and "step" not in error and tracer.steps and not error.get("driver"):
        error["step"] = len(tracer.steps) - 1
        error.setdefault("line", tracer.steps[-1]["line"])

    stdout = out.getvalue()
    result["steps"] = tracer.steps
    result["stdout"] = stdout[:MAX_STDOUT]
    result["error"] = error
    if "__wdib_result__" in ns:
        result["result"] = repr(ns["__wdib_result__"])[:20_000]
    real_stdout.write(json.dumps(result, default=repr))


def _stack_depth():
    f = sys._getframe()
    out = []
    while f is not None:
        out.append(f)
        f = f.f_back
    return out


if __name__ == "__main__":
    main()
