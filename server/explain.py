"""Error forensics: turns a raw exception into an explanation the visualizer can show."""
from __future__ import annotations

import ast
import builtins
import difflib
import re
from collections import Counter

from .values import deref, frame_by_fid, py, show

TITLES = {
    "IndexError": "Index out of range",
    "KeyError": "Missing dictionary key",
    "AttributeError": "Attribute on the wrong thing",
    "TypeError": "Wrong type of value",
    "ZeroDivisionError": "Division by zero",
    "RecursionError": "Recursion never stopped",
    "StepLimit": "Probably an infinite loop",
    "TimeLimit": "Program took too long",
    "NameError": "Unknown name",
    "SyntaxError": "Python couldn't read this line",
    "IndentationError": "Indentation problem",
    "TabError": "Mixed tabs and spaces",
    "ValueError": "Bad value",
    "UnboundLocalError": "Variable used before it was assigned",
    "AssertionError": "An assert failed",
}


# ------------------------------------------------------------------ helpers

def _lookup(step, fid, name):
    f = frame_by_fid(step, fid) if fid else None
    if f and name in f["vars"]:
        return f["vars"][name], f["fid"]
    for fr in reversed(step["frames"]):
        if name in fr["vars"]:
            return fr["vars"][name], fr["fid"]
    return None, None


def _history(steps, upto, fid, name, limit=8):
    """Changes of a variable's (shallow) value up to step `upto`."""
    hist = []
    last = None
    for i in range(upto + 1):
        s = steps[i]
        f = frame_by_fid(s, fid)
        if f is None or name not in f["vars"]:
            continue
        v = f["vars"][name]
        key = (v.get("t"), v.get("r"), repr(v.get("v")))
        if key != last:
            line = steps[i - 1]["line"] if i > 0 else s["line"]
            hist.append({"step": i, "line": line, "v": show(v, s["heap"])})
            last = key
    return hist[-limit:]


def _culprit(steps, err_step, fid, name, note=None):
    s = steps[err_step]
    v, real_fid = _lookup(s, fid, name)
    if v is None:
        return None
    hist = _history(steps, err_step, real_fid, name)
    o = deref(v, s["heap"])
    tname = {"none": "None", "ref": o.get("cls") or o.get("t")}.get(v["t"], v["t"])
    c = {"name": name, "value": show(v, s["heap"]), "type": tname, "history": hist}
    if hist:
        c["changed_step"] = hist[-1]["step"]
        c["changed_line"] = hist[-1]["line"]
    if note:
        c["note"] = note
    return c


def _line_nodes(tree, line):
    return [n for n in ast.walk(tree) if getattr(n, "lineno", None) == line]


def _names_in(node):
    seen = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id not in seen and not hasattr(builtins, n.id):
            seen.append(n.id)
    return seen


def _span(node):
    return [node.lineno, node.col_offset + 1, node.end_lineno or node.lineno,
            (node.end_col_offset or node.col_offset) + 1]


def _resolve(step, fid, node):
    """Evaluate Name / Attribute / constant-subscript chains against a snapshot."""
    heap = step["heap"]
    if isinstance(node, ast.Name):
        return _lookup(step, fid, node.id)[0]
    if isinstance(node, ast.Attribute):
        base = _resolve(step, fid, node.value)
        if base is None:
            return None
        o = deref(base, heap)
        if o.get("t") == "obj":
            return o["fields"].get(node.attr)
        return None
    return None


def _last_line_step(steps, upto, fid):
    for i in range(upto, -1, -1):
        if steps[i]["ev"] == "line" and steps[i]["fid"] == fid:
            return i
    return upto


# ------------------------------------------------------------------ main

def explain(error: dict, steps: list[dict], code: str, meta: dict) -> dict:
    e = dict(error)
    etype = e.get("type", "Error")
    e["title"] = TITLES.get(etype, etype)
    e.setdefault("culprits", [])
    lines = code.splitlines()
    line = e.get("line")
    if line and 0 < line <= len(lines):
        e["code"] = lines[line - 1].strip()

    if etype in ("SyntaxError", "IndentationError", "TabError"):
        return _syntax(e)

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return e

    if etype in ("StepLimit", "TimeLimit"):
        return _infinite(e, steps, meta)
    if not steps or "step" not in e:
        e["why"] = e.get("msg", "")
        return e

    k = e["step"]
    s = steps[k]
    fid = s["fid"]
    ls = _last_line_step(steps, k, fid)
    acc = steps[ls].get("acc") or []
    nodes = _line_nodes(tree, line) if line else []
    msg = e.get("msg", "")

    handler = {
        "IndexError": _index,
        "KeyError": _key,
        "AttributeError": _attr,
        "TypeError": _type,
        "ZeroDivisionError": _zero,
        "RecursionError": _recursion,
        "NameError": _name,
        "UnboundLocalError": _name,
    }.get(etype, _generic)
    handler(e, steps, k, fid, acc, nodes, msg, meta)

    # generic culprits when a handler found none
    if not e["culprits"] and nodes and etype not in ("RecursionError", "NameError"):
        names = []
        for n in nodes:
            if isinstance(n, ast.stmt) or isinstance(n, ast.expr):
                for nm in _names_in(n):
                    if nm not in names:
                        names.append(nm)
        for nm in names[:4]:
            c = _culprit(steps, k, fid, nm)
            if c:
                e["culprits"].append(c)
    return e


def _syntax(e):
    msg = e.get("msg", "")
    e["why"] = f"Python stopped reading your code at line {e.get('line')}: {msg}."
    hint = "Check for a missing colon, an unclosed bracket or quote, or wrong indentation."
    if "expected ':'" in msg:
        hint = "Lines that start a block (if, for, while, def, class) must end with a colon `:`."
    elif "was never closed" in msg or "unmatched" in msg:
        hint = "A bracket ( [ { was opened but never closed (or closed with the wrong kind)."
    elif "indent" in msg:
        hint = "Python uses indentation to group code. Make the block line up with 4 spaces."
    elif "invalid syntax" in msg and "=" in (e.get("text") or "") and "==" not in (e.get("text") or ""):
        hint = "Comparisons use `==`; a single `=` is assignment and isn't allowed inside conditions."
    e["hint"] = hint
    e["span"] = [e.get("line", 1), e.get("col", 1), e.get("line", 1),
                 (e.get("end_col") or (e.get("col", 1) + 1))]
    return e


def _index(e, steps, k, fid, acc, nodes, msg, meta):
    s = steps[k]
    bad = [a for a in acc if a.get("ok") is False]
    if bad:
        a = bad[0]
        cont, _ = _lookup(s, fid, a["var"])
        heap = s["heap"]
        # walk down to the container that actually failed
        path = a["var"]
        o = deref(cont, heap) if cont else {}
        fail_i, fail_idx = 0, None
        for depth, iv in enumerate(a["idx"]):
            ii = py(iv)
            items = o.get("items", [])
            if not isinstance(ii, int) or not (-len(items) <= ii < len(items)):
                fail_i, fail_idx = depth, ii
                break
            path += f"[{a['expr'][depth]}]"
            o = deref(items[ii], heap)
        n = len(o.get("items", [])) + (o.get("more") or 0)
        expr = a["expr"][fail_i]
        e["viz"] = {"kind": "oob", "var": a["var"], "idx": fail_idx, "len": n, "expr": expr,
                    "depth": fail_i, "path": [py(i) for i in a["idx"][:fail_i]]}
        if n == 0:
            e["why"] = f"`{path}` is empty, so there is no index {fail_idx} to read."
        else:
            e["why"] = (f"`{a['text']}` asks for index {fail_idx} (from `{expr}`), but `{path}` "
                        f"has only {n} item{'s' if n != 1 else ''} — valid indexes are 0 to {n - 1}.")
        if isinstance(fail_idx, int) and fail_idx == n:
            e["hint"] = ("Classic off-by-one: index len is one past the end. If you read "
                         f"`{a['var']}[i+1]`, loop with `range(len({a['var']}) - 1)`; for binary search "
                         "use `r = len(a) - 1`.")
        elif isinstance(fail_idx, int) and fail_idx < 0:
            e["hint"] = ("A negative index went past the start. Careful: Python lets a[-1] silently read the "
                         "LAST item, so the bug can hide for a few steps. Add a bound check like `j >= 0`.")
        else:
            e["hint"] = "Check the loop bounds and how the index variable is updated."
        for nd in nodes:
            if isinstance(nd, ast.Subscript) and ast.unparse(nd) == a["text"]:
                e["span"] = _span(nd)
                break
        try:
            names = _names_in(ast.parse(expr, mode="eval"))
        except SyntaxError:
            names = []
        for nm in names:
            c = _culprit(steps, k, fid, nm, note=f"used in `{expr}`")
            if c:
                e["culprits"].append(c)
        return
    if "pop from" in msg or msg == "index out of range":
        for nd in nodes:
            var = None
            if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Attribute) and nd.func.attr in (
                    "pop", "popleft") and isinstance(nd.func.value, ast.Name):
                var = nd.func.value.id
            elif isinstance(nd, ast.Call) and nd.args and isinstance(nd.args[0], ast.Name) and (
                    getattr(nd.func, "attr", None) == "heappop" or getattr(nd.func, "id", None) == "heappop"):
                var = nd.args[0].id
            if var:
                v, _ = _lookup(steps[k], fid, var)
                o = deref(v, steps[k]["heap"]) if v else {}
                if o.get("items"):
                    continue
                e["why"] = f"`{var}` is empty, so there is nothing to pop."
                fname = getattr(nd.func, "attr", None) or getattr(nd.func, "id", "pop")
                e["hint"] = f"Guard it: `if {var}:` (or `while {var}:`) before calling `{fname}()`."
                e["viz"] = {"kind": "empty", "var": var}
                e["span"] = _span(nd)
                c = _culprit(steps, k, fid, var)
                if c:
                    e["culprits"].append(c)
                return
    e["why"] = msg
    e["hint"] = "An index is outside the list. Print the index and len() right before this line."


def _key(e, steps, k, fid, acc, nodes, msg, meta):
    s = steps[k]
    bad = [a for a in acc if a.get("ok") is False]
    key = msg
    if bad:
        a = bad[0]
        cont, _ = _lookup(s, fid, a["var"])
        o = deref(cont, s["heap"]) if cont else {}
        keys = [show(kk, s["heap"]) for kk, _ in o.get("entries", [])][:12]
        key = show(a["idx"][-1], s["heap"])
        e["why"] = (f"`{a['var']}` has no key {key}. "
                    + (f"Keys it does have: {', '.join(keys)}." if keys else "It is empty."))
        e["viz"] = {"kind": "missing_key", "var": a["var"], "key": key}
        e["hint"] = (f"Use `{a['var']}.get({a['expr'][-1]}, default)`, check `if {a['expr'][-1]} in "
                     f"{a['var']}`, or use `collections.defaultdict`.")
        for nd in nodes:
            if isinstance(nd, ast.Subscript) and ast.unparse(nd) == a["text"]:
                e["span"] = _span(nd)
        for nm in _names_in(ast.parse(a["expr"][-1], mode="eval")):
            c = _culprit(steps, k, fid, nm)
            if c:
                e["culprits"].append(c)
        return
    e["why"] = f"The key {key} isn't in the dictionary."
    e["hint"] = "Use .get(key, default) or check `key in d` first."


def _attr(e, steps, k, fid, acc, nodes, msg, meta):
    s = steps[k]
    m = re.match(r"'(\w+)' object has no attribute '(\w+)'", msg)
    if not m:
        e["why"] = msg
        return
    tname, attr = m.groups()
    for nd in nodes:
        if isinstance(nd, ast.Attribute) and nd.attr == attr:
            v = _resolve(s, fid, nd.value)
            if v is not None and (tname != "NoneType" or v.get("t") == "none"):
                expr = ast.unparse(nd.value)
                base = expr.split(".")[0].split("[")[0]
                e["span"] = _span(nd)
                if tname == "NoneType":
                    e["why"] = (f"`{expr}` is None, so it has no `.{attr}`. You probably walked past the "
                                f"end of a linked list or into an empty child of a tree.")
                    e["hint"] = (f"Guard it first: `while {expr} is not None:` or `if {expr}:` before "
                                 f"using `{expr}.{attr}`. For fast/slow pointers use "
                                 f"`while fast and fast.next:`.")
                    e["viz"] = {"kind": "none", "var": base, "expr": expr, "attr": attr}
                else:
                    e["why"] = f"`{expr}` is a {tname}, and {tname} has no `.{attr}`."
                    e["hint"] = "Check which type this variable holds at this moment."
                c = _culprit(steps, k, fid, base, note=f"`{expr}` is {show(v, s['heap'])}")
                if c:
                    e["culprits"].append(c)
                return
    e["why"] = f"A {tname} value has no attribute `.{attr}`."
    e["hint"] = "Check the variable's type right before this line."


def _type(e, steps, k, fid, acc, nodes, msg, meta):
    s = steps[k]
    e["why"] = msg
    if "'NoneType'" in msg:
        for nd in nodes:
            target = None
            if isinstance(nd, ast.Subscript):
                target = nd.value
            elif isinstance(nd, ast.BinOp):
                for side in (nd.left, nd.right):
                    v = _resolve(s, fid, side)
                    if v is not None and v.get("t") == "none":
                        target = side
            elif isinstance(nd, ast.Compare):
                for side in [nd.left, *nd.comparators]:
                    v = _resolve(s, fid, side)
                    if v is not None and v.get("t") == "none":
                        target = side
            if target is not None:
                v = _resolve(s, fid, target)
                if v is not None and v.get("t") == "none":
                    expr = ast.unparse(target)
                    e["why"] = f"`{expr}` is None here, and None can't be used like that ({msg})."
                    e["hint"] = ("A common cause: a function that forgot to `return` its result (it "
                                 "returns None by default), or a list method like `.sort()` / `.append()` "
                                 "that changes the list and returns None.")
                    e["span"] = _span(target)
                    e["viz"] = {"kind": "none", "var": expr.split(".")[0], "expr": expr}
                    c = _culprit(steps, k, fid, expr.split(".")[0].split("[")[0])
                    if c:
                        e["culprits"].append(c)
                    return
    if "not supported between" in msg or "unsupported operand" in msg or "can only concatenate" in msg:
        e["hint"] = "The two sides have different types. Convert one (int(), str()) or check where it got set."
    elif "not callable" in msg:
        e["hint"] = "You used ( ) on something that isn't a function — maybe a variable shadows a function name."
    elif "argument" in msg:
        e["hint"] = "The function was called with the wrong number of arguments. Compare the call with the def line."
    else:
        e["hint"] = "Look at the type of each value on this line (shown below)."


def _zero(e, steps, k, fid, acc, nodes, msg, meta):
    s = steps[k]
    for nd in nodes:
        if isinstance(nd, ast.BinOp) and isinstance(nd.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            expr = ast.unparse(nd.right)
            e["why"] = f"`{expr}` is 0 here, and you can't divide by zero."
            e["span"] = _span(nd.right)
            for nm in _names_in(nd.right):
                c = _culprit(steps, k, fid, nm)
                if c:
                    e["culprits"].append(c)
            break
    else:
        e["why"] = "Division by zero."
    e["hint"] = "Guard against empty inputs (e.g. `if count == 0: return 0`) before dividing."


def _recursion(e, steps, k, fid, acc, nodes, msg, meta):
    calls = [s for s in steps[: k + 1] if s["ev"] == "call"]
    if not calls:
        e["why"] = "The call stack grew too deep."
        return
    rec = set(meta.get("recursive", []))
    recent = [c["fn"] for c in calls[-200:]]
    pool = [f for f in recent if f in rec] or recent
    fn = Counter(pool).most_common(1)[0][0]
    idx_of = {id(s): i for i, s in enumerate(steps[: k + 1])}
    mine = [c for c in calls if c["fn"] == fn]
    depth = max(len(s["frames"]) for s in steps[: k + 1])
    sample = []
    picked = mine[:4] + [None] + mine[-3:] if len(mine) > 7 else mine
    for c in picked:
        if c is None:
            sample.append("…")
            continue
        top = c["frames"][-1]
        sample.append(", ".join(f"{a}={show(v, c['heap'])}" for a, v in top["vars"].items()))
    e["why"] = f"`{fn}` kept calling itself — the stack reached depth {depth} without hitting a base case."
    # analyse numeric argument trends
    hint = "Every recursive function needs a base case that stops it, and each call must move closer to it."
    first = mine[0]["frames"][-1]["vars"]
    series = {}
    for arg in first:
        vals = [py(c["frames"][-1]["vars"].get(arg, {})) for c in mine]
        if len(vals) > 3 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
            series[arg] = vals
    stuck = [a for a, vals in series.items() if len(set(vals[-5:])) == 1]
    chosen = None
    if series and len(stuck) == len(series):
        same = ", ".join(f"{a}={series[a][-1]}" for a in stuck)
        hint = (f"`{fn}` is called with the same arguments ({same}) over and over, so the problem never "
                f"gets smaller. Each recursive call must shrink the input (e.g. `p - 1` instead of `p`).")
        chosen = stuck
    else:
        for arg, vals in series.items():
            if arg in stuck:
                continue
            loop_vals = list(dict.fromkeys(vals[-12:]))
            if len(loop_vals) <= 3:
                hint = (f"`{arg}` keeps bouncing between {', '.join(map(str, loop_vals))} — the recursion "
                        f"is going round in a cycle. In graph code, mark a node as visited *before* "
                        f"recursing into its neighbours.")
            elif vals[-1] < 0 <= vals[0]:
                hint = (f"`{arg}` went {vals[0]}, {vals[1]}, {vals[2]}, … {vals[-1]} — it skipped past your "
                        f"base case. Use `if {arg} <= 0` (or `<= 1`) instead of `== 0`, or add a missing "
                        f"base case.")
            elif vals[-1] > vals[0]:
                hint = f"`{arg}` is growing ({vals[0]} → {vals[-1]}) instead of shrinking toward the base case."
            else:
                hint = (f"`{arg}` keeps changing ({vals[0]} → {vals[-1]}) but never reaches a value where the "
                        f"base case returns. Check the base case condition.")
            chosen = [arg]
            break
    for arg in chosen or []:
        vals = series[arg]
        e["culprits"].append({"name": arg, "value": str(vals[-1]), "type": "int",
                              "history": [{"step": idx_of[id(c)], "line": c["line"], "v": str(v)}
                                          for c, v in list(zip(mine, vals))[-8:]],
                              "note": "value on each call"})
    e["hint"] = hint
    e["viz"] = {"kind": "recursion", "fn": fn, "depth": depth, "calls": sample}


def _name(e, steps, k, fid, acc, nodes, msg, meta):
    m = re.search(r"name '(\w+)'", msg) or re.search(r"variable '(\w+)'", msg)
    name = m.group(1) if m else "?"
    known = set(dir(builtins)) | set(meta.get("funcs", []))
    for s in steps[: k + 1]:
        for f in s["frames"]:
            known.update(f["vars"].keys())
    close = difflib.get_close_matches(name, sorted(known), n=2, cutoff=0.7)
    if e.get("type") == "UnboundLocalError":
        e["why"] = (f"`{name}` is assigned somewhere inside this function, so Python treats it as local — "
                    f"but you read it before giving it a value.")
        e["hint"] = f"Assign `{name}` before using it, or pass it in as a parameter."
    else:
        e["why"] = f"Python doesn't know any variable or function called `{name}` at this point."
        e["hint"] = (f"Did you mean `{close[0]}`?" if close else
                     f"Define `{name}` before this line (check spelling and capitalization).")
    for nd in nodes:
        if isinstance(nd, ast.Name) and nd.id == name:
            e["span"] = _span(nd)
            break


def _generic(e, steps, k, fid, acc, nodes, msg, meta):
    e["why"] = msg or e.get("type")
    if e.get("type") == "ValueError" and "unpack" in msg:
        e["hint"] = "The number of variables on the left doesn't match the number of values on the right."
    elif e.get("type") == "ValueError" and "invalid literal" in msg:
        e["hint"] = "int() got text that isn't a number. Check the input (strip spaces, split correctly)."
    elif e.get("type") == "AssertionError":
        e["hint"] = "The condition in your assert was False. Compare the values below with what you expected."
    else:
        e["hint"] = "Look at the values of the variables on this line, shown below."


def _infinite(e, steps, meta):
    if not steps:
        e["why"] = e.get("msg")
        return e
    window = steps[-400:]
    lines = Counter(s["line"] for s in window if s["ev"] == "line")
    hot = lines.most_common(1)[0][0] if lines else steps[-1]["line"]
    loops = [lp for lp in meta.get("loops", []) if lp["line"] <= hot <= (lp["end"] or lp["line"])]
    last = steps[-1]
    fid = last["fid"]
    e["step"] = len(steps) - 1
    e["line"] = hot
    if len(last["frames"]) > 40:  # deep stack: really a runaway recursion
        e["title"] = TITLES["RecursionError"]
        _recursion(e, steps, len(steps) - 1, fid, [], [], "", meta)
        e["line"] = last["line"]
        return e
    calls = sum(1 for s in window if s["ev"] == "call")
    if calls > len(window) / 4 and not loops:
        e["why"] = "Your program kept making function calls and never finished."
        e["hint"] = "Check the recursion's base case."
        return e
    if not loops:
        e["why"] = f"Line {hot} ran over and over and the program never finished."
        e["hint"] = "Make sure each loop iteration moves toward the exit condition."
        return e
    lp = max(loops, key=lambda x: x["line"])  # innermost
    e["line"] = lp["line"]
    runs = sum(1 for s in steps if s["ev"] == "line" and s["line"] == lp["line"])
    frozen, cycling = [], {}
    for nm in lp["names"]:
        vals = []
        for s in window:
            v, _ = _lookup(s, fid, nm)
            if v is not None:
                sv = show(v, s["heap"])
                if not vals or vals[-1] != sv:
                    vals.append(sv)
        distinct = list(dict.fromkeys(vals))
        if len(distinct) == 1:
            frozen.append(nm)
        elif 1 < len(distinct) <= 4 and len(vals) > 2 * len(distinct):
            cycling[nm] = distinct
    kw = "while" if lp["kind"] == "while" else "for"
    e["title"] = "Infinite loop" if e["type"] == "StepLimit" else e["title"]
    if cycling:
        nm, vals = next(iter(cycling.items()))
        e["why"] = (f"The loop `{kw} {lp['cond']}` on line {lp['line']} ran {runs}+ times. `{nm}` keeps "
                    f"cycling through {', '.join(vals)} instead of making progress.")
        e["hint"] = ("Values that go round in a circle usually mean two things point at each other "
                     "(e.g. parent[a] = b and parent[b] = a), or a pointer is reset every iteration.")
        frozen = list(cycling) + frozen
    elif frozen and lp["kind"] == "while":
        e["why"] = (f"The loop `{kw} {lp['cond']}` on line {lp['line']} ran {runs}+ times. "
                    f"{', '.join('`'+f+'`' for f in frozen)} never changed, so the condition stays True forever.")
        e["hint"] = (f"Update {' / '.join(frozen)} inside the loop so it moves toward ending "
                     f"(e.g. `i += 1`, `lo = mid + 1`, `cur = cur.next`).")
    else:
        e["why"] = f"The loop on line {lp['line']} (`{kw} {lp['cond']}`) ran {runs}+ times without finishing."
        e["hint"] = ("Check that the loop condition eventually becomes False. If your input is just large, "
                     "use a smaller one — the visualizer records up to 3000 steps.")
    e["viz"] = {"kind": "loop", "line": lp["line"], "frozen": frozen, "runs": runs}
    for nm in (frozen or lp["names"])[:4]:
        c = _culprit(steps, len(steps) - 1, fid, nm, note="never changed" if nm in frozen else None)
        if c:
            e["culprits"].append(c)
    return e
