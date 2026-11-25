"""Wrong-answer forensics: the program finished, but returned the wrong value. Find out where it went wrong.

Works on a traced run of one test case. The strategy:
  * a list answer: find the first position that differs, then find every write to that position.
    - never written  -> it kept its initial value; explain which loop stopped short and why
    - written wrongly -> point at the line and the values that produced the bad number
    - too short / too long -> the missing item was never appended / the extra one was appended here
  * anything else: point at the step where the returned variable last changed, with its history.
"""
from __future__ import annotations

import ast

from .explain import _culprit, _names_in
from .values import deref, frame_by_fid, is_prim, py, show

_SAFE = {"len": len, "min": min, "max": max, "abs": abs}


# ---------------------------------------------------------------- small helpers

def _fmt(v) -> str:
    return repr(v)


def _plain(v, heap):
    """Encoded value -> a Python value good enough for evaluating loop bounds."""
    if is_prim(v):
        return py(v)
    o = deref(v, heap)
    if o.get("t") in ("list", "tuple", "deque", "set"):
        return [_plain(x, heap) if is_prim(x) else None for x in o["items"]]
    if o.get("t") == "dict":
        return {py(k): None for k, _ in o["entries"] if is_prim(k)}
    return None


def _eval(expr: ast.expr, frame, heap):
    """Evaluate a small expression (like `len(nums) - 1`) against a snapshot frame, or None."""
    for n in ast.walk(expr):
        if not isinstance(n, (ast.Name, ast.Constant, ast.BinOp, ast.UnaryOp, ast.Load, ast.operator,
                              ast.unaryop, ast.Call)):
            return None
        if isinstance(n, ast.Call) and not (isinstance(n.func, ast.Name) and n.func.id in _SAFE):
            return None
    env = dict(_SAFE)
    for name in _names_in(expr):
        if name in frame["vars"]:
            env[name] = _plain(frame["vars"][name], heap)
    try:
        return eval(compile(ast.Expression(body=expr), "<bound>", "eval"), {"__builtins__": {}}, env)  # noqa: S307
    except Exception:
        return None


def _jump(label, step, line=None):
    j = {"label": label, "step": step}
    if line:
        j["line"] = line
    return j


def _refs_to(frame, oid):
    return [k for k, v in frame["vars"].items() if v.get("t") == "ref" and v["r"] == oid]


def _source_line(code_lines, line):
    return code_lines[line - 1].strip() if 0 < line <= len(code_lines) else ""


def _store_lines(tree, names):
    """Lines that assign into names[...]: line -> slice expression of the first index."""
    out = {}
    for n in ast.walk(tree):
        targets = []
        if isinstance(n, ast.Assign):
            targets = n.targets
        elif isinstance(n, (ast.AugAssign, ast.AnnAssign)):
            targets = [n.target]
        for t in targets:
            for sub in ast.walk(t):
                if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) and sub.value.id in names:
                    out.setdefault(n.lineno, (sub.value.id, sub.slice, n))
    return out


def _append_lines(tree, names):
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                and n.func.value.id in names and n.func.attr in ("append", "insert", "extend"):
            out.setdefault(n.lineno, n)
    return out


def _enclosing_loop(meta, line):
    best = None
    for lp in meta.get("loops", []):
        if lp["line"] <= line <= (lp["end"] or lp["line"]) and lp["line"] != line:
            if best is None or lp["line"] > best["line"]:
                best = lp
    return best


def _var_values(steps, upto, fid, name):
    """Distinct successive values a variable took in one frame, as (step, python value)."""
    vals = []
    last = object()
    for k in range(upto + 1):
        f = frame_by_fid(steps[k], fid)
        if f is None or name not in f["vars"]:
            continue
        v = f["vars"][name]
        pv = py(v) if is_prim(v) else show(v, steps[k]["heap"])
        if pv != last:
            vals.append((k, pv))
            last = pv
    return vals


def _seq(vals, limit=8):
    shown = [_fmt(v) for _, v in vals]
    if len(shown) > limit:
        shown = shown[:3] + ["…"] + shown[-3:]
    return ", ".join(shown)


# ---------------------------------------------------------------- loop explanation

def _loop_story(steps, upto, fid, meta, tree, write_line, index_expr, want, code_lines):
    """Explain why a loop never produced the index `want` at `write_line`. Returns (detail lines, hint, jumps)."""
    detail, jumps = [], []
    hint = None
    loop = _enclosing_loop(meta, write_line)
    if not loop:
        return detail, hint, jumps, None
    loop_src = _source_line(code_lines, loop["line"])
    node = next((n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While)) and n.lineno == loop["line"]),
                None)
    var = None
    if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
        var = node.target.id
    elif isinstance(index_expr, ast.Name):
        var = index_expr.id
    if var:
        vals = [v for _, v in _var_values(steps, upto, fid, var)]
        if vals:
            detail.append(f"The loop on line {loop['line']} (`{loop_src.rstrip(':')}`) ran with "
                          f"`{var}` = {_seq([(0, v) for v in vals])}, and then stopped.")
    # how the index on the write line relates to the loop variable
    if index_expr is not None and var:
        idx_txt = ast.unparse(index_expr)
        if isinstance(index_expr, ast.Name) and index_expr.id == var:
            detail.append(f"Line {write_line} writes `[{idx_txt}]`, so it would need `{var} = {want}` "
                          f"to fill index {want}, and the loop never got there.")
        else:
            detail.append(f"Line {write_line} writes index `{idx_txt}`, which never came out as {want}.")
    # what the range really was
    if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) \
            and node.iter.func.id == "range":
        first = next((k for k in range(upto + 1) if steps[k]["ev"] == "line" and steps[k]["line"] == loop["line"]
                      and steps[k]["fid"] == fid), None)
        if first is not None:
            frame = frame_by_fid(steps[first], fid)
            heap = steps[first]["heap"]
            args = [_eval(a, frame, heap) for a in node.iter.args] if frame else []
            if args and all(isinstance(a, int) for a in args):
                rng = range(*args)
                arg_src = ", ".join(ast.unparse(a) for a in node.iter.args)
                vals = list(rng)
                body = (", ".join(map(str, vals)) if len(vals) <= 8 else
                        f"{vals[0]}, {vals[1]}, …, {vals[-1]}") if vals else "nothing at all"
                stop = rng.stop
                detail.append(f"`range({arg_src})` is `range({', '.join(map(str, args))})`, which gives {body}. "
                              f"A range stops *before* its end value ({stop}).")
                jumps.append(_jump(f"see the loop start (line {loop['line']})", first, loop["line"]))
                if vals and isinstance(want, int) and want > vals[-1] and rng.step == 1:
                    end_src = ast.unparse(node.iter.args[-1] if len(node.iter.args) > 1 else node.iter.args[0])
                    hint = (f"The loop has to reach index {want}, so its end must be at least {want + 1}. "
                            f"Look at `{end_src}` on line {loop['line']}: is that `- 1` (or bound) right? "
                            f"`range(len(x))` already stops at the last index.")
                elif vals and isinstance(want, int) and want < vals[0]:
                    hint = (f"The loop starts at {vals[0]}, so index {want} is skipped. "
                            f"Check the start value of the range on line {loop['line']}.")
    elif loop["kind"] == "while":
        hint = (f"Check the condition `{loop['cond']}` on line {loop['line']}: it became false before "
                f"index {want} was handled.")
    return detail, hint, jumps, (loop["line"] if hint else None)


# ---------------------------------------------------------------- main entry

def diagnose(problem: dict, args: list, got, exp, steps: list[dict], code: str, meta: dict,
             return_step: int | None) -> dict | None:
    if return_step is None or not steps:
        return None
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    code_lines = code.splitlines()
    ret = steps[return_step]
    fid = ret["fid"]
    frame = frame_by_fid(ret, fid)
    ret_line = ret["line"]
    ret_src = _source_line(code_lines, ret_line)

    # which object/variable holds the answer?
    in_place = problem.get("output") == "arg0"
    if in_place:
        pname = problem["params"][0]
        call = next((k for k in range(return_step, -1, -1) if steps[k]["ev"] == "call" and steps[k]["fid"] == fid),
                    0)
        v = frame_by_fid(steps[call], fid)["vars"].get(pname) if frame_by_fid(steps[call], fid) else None
        ans_name, ans_val = pname, v
    else:
        ans_val = ret.get("ret")
        ans_name = None
        if ret_src.startswith("return "):
            expr = ret_src[len("return "):].strip()
            if expr.isidentifier():
                ans_name = expr
    if ans_val is None:
        return None

    unordered = problem.get("compare", "exact").startswith("unordered")
    oid = ans_val["r"] if ans_val.get("t") == "ref" else None
    obj = ret["heap"].get(oid) if oid else None
    if (oid and obj and obj.get("t") == "list" and isinstance(got, list) and isinstance(exp, list)
            and not unordered and problem.get("ret") not in ("linked", "tree", "nary")):
        names = _refs_to(frame, oid) if frame else []
        if ans_name and ans_name not in names:
            names.append(ans_name)
        out = _list_diagnosis(steps, return_step, fid, meta, tree, code_lines, oid, names, got, exp)
        if out:
            out["oid"] = oid
            return out
    return _value_diagnosis(steps, return_step, fid, tree, code_lines, ret_line, ret_src, ans_name, got, exp,
                            in_place)


def _writes_to(steps, upto, fid, oid, names, tree, index):
    """Steps (the line step that did it) that wrote position `index` of the list oid."""
    store = _store_lines(tree, set(names))
    hits = []
    for k in range(1, upto + 1):
        prev = steps[k - 1]
        # recorded change in the heap
        for op in steps[k].get("ops", []):
            if op.get("oid") != oid:
                continue
            if (op["k"] == "set" and op.get("i") == index) or (op["k"] == "swap" and index in (op["i"], op["j"])) \
                    or (op["k"] in ("append", "insert") and op.get("i") == index):
                hits.append(k - 1)
                break
        else:
            # a store that wrote the same value it already had doesn't show up as a change
            if prev["ev"] == "line" and prev["line"] in store and prev["fid"] == fid:
                for a in prev.get("acc") or []:
                    if a["var"] in names and a["idx"] and py(a["idx"][0]) == index:
                        hits.append(k - 1)
                        break
    return hits


def _list_diagnosis(steps, R, fid, meta, tree, code_lines, oid, names, got, exp):
    name = names[0] if names else "the result"
    heap = steps[R]["heap"]

    # where was the list made?
    born = next((k for k in range(R + 1) if oid in steps[k]["heap"]), None)
    born_line = steps[born - 1]["line"] if born else None

    if len(got) == len(exp):
        d = next((i for i, (g, e) in enumerate(zip(got, exp)) if g != e), None)
        if d is None:
            return None
        writes = _writes_to(steps, R, fid, oid, names, tree, d)
        base = {"var": name, "index": d, "expected_item": _fmt(exp[d]), "got_item": _fmt(got[d])}
        if not writes:
            summary = (f"`{name}[{d}]` was never written. It still holds `{_fmt(got[d])}`, the value it got when "
                       f"`{name}` was created" + (f" on line {born_line}" if born_line else "") +
                       f". It should be `{_fmt(exp[d])}`.")
            # learn from the positions that *were* written
            store = _store_lines(tree, set(names))
            appends = _append_lines(tree, set(names))
            write_line = next(iter(store), None) or next(iter(appends), None)
            idx_expr = store[write_line][1] if write_line in store else None
            detail, hint, jumps, fix_line = ([], None, [], None)
            if write_line:
                detail, hint, jumps, fix_line = _loop_story(steps, R, fid, meta, tree, write_line, idx_expr, d,
                                                            code_lines)
            if born:
                jumps.insert(0, _jump(f"see where {name} was created (line {born_line})", born - 1, born_line))
            return {**base, "kind": "never_written", "summary": summary, "detail": detail,
                    "hint": hint or f"Every position of `{name}` has to be filled. Find the loop that writes "
                                    f"`{name}[...]` and check that it reaches index {d}.",
                    "line": fix_line or write_line or born_line, "jumps": jumps, "culprits": []}
        # written, but with the wrong value: look at the last write
        w = writes[-1]
        wline = steps[w]["line"]
        src = _source_line(code_lines, wline)
        summary = (f"`{name}[{d}]` should be `{_fmt(exp[d])}`, but line {wline} set it to `{_fmt(got[d])}` "
                   f"(step {w + 1}).")
        detail = [f"That line is `{src}`."]
        culprits = []
        used = []
        for n in ast.walk(tree):
            if getattr(n, "lineno", None) != wline:
                continue
            if isinstance(n, (ast.Assign, ast.AugAssign)):
                used = _names_in(n.value)
                break
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("append", "insert"):
                used = [x for a in n.args for x in _names_in(a)]
                break
        for nm in used[:4]:
            if nm in names:
                continue
            c = _culprit(steps, w, steps[w]["fid"], nm)
            if c:
                culprits.append(c)
        if culprits:
            vals = ", ".join(f"`{c['name']}` = `{c['value']}`" for c in culprits)
            detail.append(f"At that moment {vals}. Which of these isn't what you expected?")
        if len(writes) > 1:
            detail.append(f"`{name}[{d}]` was written {len(writes)} times; this was the last one.")
        jumps = [_jump(f"go to the step that wrote {name}[{d}]", w, wline)]
        if len(writes) > 1:
            jumps.append(_jump("see the first write", writes[0], steps[writes[0]]["line"]))
        return {**base, "kind": "wrong_write", "summary": summary, "detail": detail, "line": wline,
                "jumps": jumps, "culprits": culprits,
                "hint": "Step back from that write and check each value it used against what you work out by hand."}

    # different lengths
    if len(got) < len(exp):
        d = len(got)
        summary = (f"`{name}` has {len(got)} item(s) but should have {len(exp)}. "
                   f"The first missing one is `{_fmt(exp[d])}` at index {d}.")
        appends = _append_lines(tree, set(names))
        write_line = next(iter(appends), None) or next(iter(_store_lines(tree, set(names))), None)
        detail, hint, jumps, fix_line = ([], None, [], None)
        if write_line:
            detail, hint, jumps, fix_line = _loop_story(steps, R, fid, meta, tree, write_line, None, d, code_lines)
            detail.insert(0, f"Line {write_line} adds items to `{name}`; it ran {len(got)} time(s).")
        return {"kind": "too_short", "var": name, "index": d, "expected_item": _fmt(exp[d]), "summary": summary,
                "detail": detail, "line": fix_line or write_line, "jumps": jumps, "culprits": [],
                "hint": hint or f"Find why the code that adds to `{name}` stopped early."}
    d = len(exp)
    writes = _writes_to(steps, R, fid, oid, names, tree, d)
    summary = (f"`{name}` has {len(got)} item(s) but should have {len(exp)}. "
               f"The first extra one is `{_fmt(got[d])}` at index {d}.")
    jumps, line = [], None
    if writes:
        line = steps[writes[0]]["line"]
        summary += f" It was added on line {line} (step {writes[0] + 1})."
        jumps.append(_jump(f"go to the step that added {name}[{d}]", writes[0], line))
    return {"kind": "too_long", "var": name, "index": d, "got_item": _fmt(got[d]), "summary": summary,
            "detail": [], "line": line, "jumps": jumps, "culprits": [],
            "hint": "Check the condition that decides whether to add an item, and when the loop should stop."}


def _value_diagnosis(steps, R, fid, tree, code_lines, ret_line, ret_src, ans_name, got, exp, in_place):
    ret = steps[R]
    if got is None and not in_place and not ret_src.startswith("return"):
        last = next((k for k in range(R, -1, -1) if steps[k]["ev"] == "line" and steps[k]["fid"] == fid), R)
        return {"kind": "no_return",
                "summary": f"Your function finished without reaching a `return`, so Python returned `None`. "
                           f"The last line it ran was line {steps[last]['line']}.",
                "detail": [f"Expected `{_fmt(exp)}`."], "line": steps[last]["line"],
                "jumps": [_jump("go to the end of the function", R, steps[last]["line"])], "culprits": [],
                "hint": "Make sure every path through the function ends with `return <answer>`."}
    culprits = []
    names = [ans_name] if ans_name else []
    if not names and ret_src.startswith("return "):
        try:
            names = _names_in(ast.parse(ret_src[len("return "):].strip(), mode="eval"))
        except SyntaxError:
            names = []
    for nm in names[:3]:
        c = _culprit(steps, R, fid, nm)
        if c:
            culprits.append(c)
    summary = f"Your function returned `{_fmt(got)}` from line {ret_line}, but the answer is `{_fmt(exp)}`."
    detail, jumps, line = [], [], ret_line
    if culprits and culprits[0].get("changed_step") is not None:
        c = culprits[0]
        hist = c["history"]
        detail.append(f"`{c['name']}` took the values " + ", ".join(f"`{h['v']}`" for h in hist) +
                      f". Its last change was on line {c['changed_line']} (step {c['changed_step'] + 1}).")
        jumps.append(_jump(f"go to where {c['name']} last changed (line {c['changed_line']})",
                           max(0, c["changed_step"] - 1), c["changed_line"]))
        line = c["changed_line"]
        if isinstance(exp, (int, float)) and any(_num(h["v"]) == exp for h in hist):
            k = next(h for h in hist if _num(h["v"]) == exp)
            detail.append(f"It *was* `{_fmt(exp)}` at step {k['step'] + 1} (line {k['line']}), "
                          f"but changed again afterwards.")
            jumps.append(_jump(f"see when {c['name']} was {_fmt(exp)}", k["step"], k["line"]))
    elif in_place:
        summary = f"After your function ran, `{ans_name}` is `{_fmt(got)}`, but it should be `{_fmt(exp)}`."
    return {"kind": "wrong_value", "summary": summary, "detail": detail, "line": line, "jumps": jumps,
            "culprits": culprits,
            "hint": "Follow the value backwards from the return: find the first step where it stops matching what "
                    "you expect by hand."}


def _num(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        try:
            return float(s)
        except (TypeError, ValueError):
            return None
