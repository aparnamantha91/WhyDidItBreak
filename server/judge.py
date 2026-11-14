"""Problem mode: wraps a user's function in a test harness, judges it, and traces one case."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from functools import lru_cache

from . import problems, tracer

JUDGE_RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "judge_runner.py")
CASE_TIMEOUT = 2.0

# Runs before the user's code (untraced), so ListNode / TreeNode exist like they do on LeetCode.
PRELUDE = '''\
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def __wdib_ll__(vals):
    head = None
    for v in reversed(vals):
        head = ListNode(v, head)
    return head


def __wdib_unll__(node):
    out = []
    while node is not None and len(out) < 500:
        out.append(getattr(node, "val", "?"))
        node = getattr(node, "next", None)
    return out


def __wdib_tree__(vals):
    if not vals or vals[0] is None:
        return None
    root = TreeNode(vals[0])
    queue = [root]
    i = 1
    while queue and i < len(vals):
        node = queue.pop(0)
        if i < len(vals) and vals[i] is not None:
            node.left = TreeNode(vals[i])
            queue.append(node.left)
        i += 1
        if i < len(vals) and vals[i] is not None:
            node.right = TreeNode(vals[i])
            queue.append(node.right)
        i += 1
    return root


def __wdib_untree__(root):
    out = []
    queue = [root]
    while queue and len(out) < 500:
        node = queue.pop(0)
        if node is None:
            out.append(None)
            continue
        out.append(getattr(node, "val", "?"))
        queue.append(getattr(node, "left", None))
        queue.append(getattr(node, "right", None))
    while out and out[-1] is None:
        out.pop()
    return out


def __wdib_norm__(v):
    if isinstance(v, (list, tuple)):
        return [__wdib_norm__(x) for x in v]
    if isinstance(v, (set, frozenset)):
        return sorted((__wdib_norm__(x) for x in v), key=repr)
    if isinstance(v, dict):
        return {k: __wdib_norm__(x) for k, x in v.items()}
    return v
'''

_BUILD = {"linked": "__wdib_ll__({})", "tree": "__wdib_tree__({})"}
_UNBUILD = {"linked": "__wdib_unll__({})", "tree": "__wdib_untree__({})"}


def driver(problem: dict, args: list) -> str:
    """Source that calls the user's function on one test case. Runs after the user's code, untraced."""
    kinds = problem.get("kinds", {})
    parts = [_BUILD.get(kinds.get(name, ""), "{}").format(repr(a))
             for name, a in zip(problem["params"], args)]
    value = "__wdib_in__[0]" if problem.get("output") == "arg0" else "__wdib_out__"
    value = _UNBUILD.get(problem.get("ret", ""), "{}").format(value)
    return (
        f"__wdib_in__ = [{', '.join(parts)}]\n"
        f"__wdib_out__ = {problem['fn']}(*__wdib_in__)\n"
        f"__wdib_result__ = __wdib_norm__({value})\n"
    )


def show_input(problem: dict, args: list) -> str:
    return ", ".join(f"{n} = {a!r}" for n, a in zip(problem["params"], args))


def parse_custom(problem: dict, text: str) -> list:
    """One argument per line, as Python literals. `name = value` is accepted too."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    params = problem["params"]
    if len(lines) != len(params):
        raise ValueError(f"Expected {len(params)} line(s), one per argument: {', '.join(params)}")
    args = []
    for name, ln in zip(params, lines):
        if ln.startswith(name) and ln[len(name):].lstrip().startswith("="):
            ln = ln[len(name):].lstrip()[1:].strip()
        try:
            args.append(ast.literal_eval(ln))
        except (ValueError, SyntaxError):
            raise ValueError(f"Couldn't read `{name}`: {ln!r} is not a Python value") from None
    return args


# ---------------------------------------------------------------- running

def _run_cases(code: str, problem: dict, cases: list[list]) -> dict:
    payload = {"code": code, "prelude": PRELUDE, "timeout": CASE_TIMEOUT,
               "drivers": [driver(problem, a) for a in cases]}
    wall = CASE_TIMEOUT * min(len(cases), 2) + 6
    with tempfile.TemporaryDirectory(prefix="wdib-") as cwd:
        try:
            proc = subprocess.run([sys.executable, "-E", "-s", JUDGE_RUNNER], input=json.dumps(payload),
                                  capture_output=True, text=True, timeout=wall, cwd=cwd)
        except subprocess.TimeoutExpired:
            return {"cases": [{"status": "timeout"}] + [{"status": "skipped"}] * (len(cases) - 1)}
    if proc.returncode != 0 or not proc.stdout.strip():
        err = {"type": "InternalError", "msg": (proc.stderr or "judge crashed")[-500:], "line": None}
        return {"cases": [{"status": "error", "error": err} for _ in cases]}
    return json.loads(proc.stdout)


def _value(text: str | None):
    """(parsed ok?, value) from the repr the child printed."""
    try:
        return True, ast.literal_eval(text or "None")
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return False, text


@lru_cache(maxsize=2048)
def _expected(problem_id: str, args_repr: str):
    problem = problems.by_id(problem_id)
    case = _run_cases(problem["solution"], problem, [ast.literal_eval(args_repr)])["cases"][0]
    if case["status"] != "ok":
        why = case["error"]["msg"] if case.get("error") else case["status"]
        raise ValueError(f"this input doesn't fit the problem (the reference solution fails on it: {why})")
    return _value(case["result"])[1]


def expected(problem: dict, args: list):
    return _expected(problem["id"], repr(args))


def _key(v):
    return repr(v)


def same(problem: dict, got, exp) -> bool:
    mode = problem.get("compare", "exact")
    try:
        if mode == "unordered":
            return isinstance(got, list) and sorted(got, key=_key) == sorted(exp, key=_key)
        if mode == "unordered2":
            if not isinstance(got, list) or not all(isinstance(x, list) for x in got):
                return False
            norm = lambda rows: sorted((sorted(r, key=_key) for r in rows), key=_key)  # noqa: E731
            return norm(got) == norm(exp)
        if mode == "float":
            return isinstance(got, (int, float)) and not isinstance(got, bool) and abs(got - exp) < 1e-6
    except TypeError:
        return False
    return got == exp and isinstance(got, bool) == isinstance(exp, bool)  # True is not 1 here


def _diff(got, exp) -> str | None:
    if got is None and exp is not None:
        return "Your function returned `None`. Is a `return` missing on some path?"
    if isinstance(got, list) and isinstance(exp, list):
        if len(got) != len(exp):
            return f"Expected {len(exp)} item(s) but got {len(got)}."
        for i, (g, e) in enumerate(zip(got, exp)):
            if g != e:
                return f"First difference at index {i}: expected `{e!r}`, got `{g!r}`."
    if type(got) is not type(exp) and not (isinstance(got, (int, float)) and isinstance(exp, (int, float))):
        return f"Expected a `{type(exp).__name__}` but got a `{type(got).__name__}`."
    return None


def _verdict(problem: dict, args: list, case: dict) -> dict:
    exp = expected(problem, args)
    v = {"status": case["status"], "input": show_input(problem, args), "expected": repr(exp),
         "stdout": case.get("stdout", "")}
    if case["status"] == "ok":
        ok, got = _value(case["result"])
        v["got"] = repr(got) if ok else str(got)
        if ok and same(problem, got, exp):
            v["status"] = "pass"
        else:
            v["status"] = "wrong"
            unordered = problem.get("compare", "exact").startswith("unordered")
            d = _diff(got, exp) if ok and not (unordered and isinstance(got, list)) else None
            if d:
                v["diff"] = d
            if unordered:
                v["note"] = "Order doesn't matter for this problem."
    elif case["status"] == "error":
        v["error"] = case["error"]
    return v


def _missing(code: str, problem: dict) -> dict | None:
    """A friendly error when the required function isn't there (instead of a NameError in the harness)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == problem["fn"]:
            return None
    sig = f"{problem['fn']}({', '.join(problem['params'])})"
    return {"type": "MissingFunction", "msg": f"{problem['fn']} is not defined", "line": None,
            "title": "The function is missing",
            "why": f"The tests call `{sig}`, but your code doesn't define a top-level function with that name.",
            "hint": f"Keep the line `def {sig}:` from the starter code and write your solution inside it.",
            "culprits": []}


def cases_of(problem: dict, test: int | None, custom: str | None) -> list:
    if custom is not None:
        return parse_custom(problem, custom)
    tests = problem["tests"]
    return tests[max(0, min(test or 0, len(tests) - 1))]


def submit(code: str, problem: dict) -> dict:
    tests = problem["tests"]
    missing = _missing(code, problem)
    if missing:
        return {"results": [], "passed": 0, "total": len(tests), "fatal": missing}
    raw = _run_cases(code, problem, tests)
    if "syntax" in raw:
        e = raw["syntax"]
        return {"results": [], "passed": 0, "total": len(tests),
                "fatal": {**e, "title": "Syntax error", "why": f"{e['msg']} (line {e['line']})", "culprits": []}}
    results = []
    for i, (args, case) in enumerate(zip(tests, raw["cases"])):
        if case["status"] == "skipped":
            results.append({"index": i, "status": "skipped", "input": show_input(problem, args)})
            continue
        results.append({"index": i, **_verdict(problem, args, case)})
    passed = sum(r["status"] == "pass" for r in results)
    return {"results": results, "passed": passed, "total": len(tests)}


def trace(code: str, problem: dict, args: list) -> dict:
    """Full visual trace of one case, plus the verdict from an untraced run of the same case."""
    missing = _missing(code, problem)
    if missing:
        return {"steps": [], "pool": [], "stdout": "", "error": missing, "meta": {},
                "verdict": {"status": "error", "input": show_input(problem, args), "error": missing}}
    res = tracer.run(code, prelude=PRELUDE, driver=driver(problem, args))
    err = res.get("error")
    if err and err.get("type") in ("SyntaxError", "IndentationError", "TabError"):
        res["verdict"] = {"status": "error", "input": show_input(problem, args), "error": err}
        return res
    verdict = _verdict(problem, args, _run_cases(code, problem, [args])["cases"][0])
    res["verdict"] = verdict
    if err and err.get("driver"):
        err.setdefault("culprits", [])
        err["title"] = "The call itself failed"
        err["why"] = (f"The tests call `{problem['fn']}({', '.join(problem['params'])})`, "
                      f"and Python refused: {err.get('msg', '')}")
        err["hint"] = "Check that your function takes exactly the parameters shown in the starter code."
    elif err and err.get("type") in ("StepLimit", "TimeLimit") and verdict["status"] in ("pass", "wrong"):
        # the code does finish, it is just longer than the visualizer records
        res["error"] = None
        res["truncated"] = True
    fn = problem["fn"]
    for i in range(len(res["steps"]) - 1, -1, -1):
        s = res["steps"][i]
        if s["ev"] == "return" and s["fn"] == fn:
            res["return_step"] = i
            break
    return res


# ---------------------------------------------------------------- API views

def info(problem: dict) -> dict:
    return {k: problem[k] for k in ("id", "title", "level", "topic")}


def detail(problem: dict, lesson: dict | None) -> dict:
    visible = problem.get("visible", 3)
    notes = problem.get("explain", [])
    cases = []
    for i, args in enumerate(problem["tests"][:visible]):
        cases.append({"index": i, "input": show_input(problem, args), "expected": repr(expected(problem, args)),
                      "explain": notes[i] if i < len(notes) else None})
    return {
        **info(problem),
        "statement": problem["statement"],
        "constraints": problem.get("constraints", []),
        "hints": problem.get("hints", []),
        "fn": problem["fn"],
        "params": problem["params"],
        "starter": problem["starter"],
        "solution": problem["solution"],
        "cases": cases,
        "total": len(problem["tests"]),
        "lesson": {k: lesson[k] for k in ("id", "title", "concept", "code", "buggy")} if lesson else None,
    }
