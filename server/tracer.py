"""Runs user code in an isolated subprocess and post-processes the trace."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from . import analyze, explain, narrate

RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner.py")
WALL_TIMEOUT = 8.0


def run_raw(code: str, stdin: str = "") -> dict:
    with tempfile.TemporaryDirectory(prefix="wdib-") as cwd:
        try:
            proc = subprocess.run(
                [sys.executable, "-E", "-s", RUNNER],
                input=json.dumps({"code": code, "stdin": stdin}),
                capture_output=True,
                text=True,
                timeout=WALL_TIMEOUT,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired:
            return {"steps": [], "stdout": "", "error": {
                "type": "TimeLimit", "msg": f"Program was stopped after {WALL_TIMEOUT:.0f}s"}}
    if proc.returncode != 0 or not proc.stdout.strip():
        return {"steps": [], "stdout": "", "error": {
            "type": "InternalError", "msg": (proc.stderr or "tracer crashed")[-2000:]}}
    return json.loads(proc.stdout)


def run(code: str, stdin: str = "") -> dict:
    raw = run_raw(code, stdin)
    meta = analyze.code_meta(code)
    steps = raw["steps"]
    narrate.annotate(steps, meta)
    error = raw.get("error")
    if error:
        error = explain.explain(error, steps, code, meta)
    pool = compact(steps)
    return {"steps": steps, "pool": pool, "stdout": raw["stdout"], "error": error, "meta": meta}


def compact(steps: list[dict]) -> list:
    """Deduplicate frames and heap objects across steps (they repeat a lot).

    After this, step["frames"] is a pool index of a list of pool indexes and
    step["heap"] is a pool index of a {oid: pool index} map.
    """
    pool: list = []
    seen: dict[str, int] = {}

    def intern(obj) -> int:
        key = json.dumps(obj, separators=(",", ":"))
        i = seen.get(key)
        if i is None:
            i = seen[key] = len(pool)
            pool.append(obj)
        return i

    for s in steps:
        s["frames"] = intern([intern(f) for f in s["frames"]])
        s["heap"] = intern({oid: intern(o) for oid, o in s["heap"].items()})
    return pool
