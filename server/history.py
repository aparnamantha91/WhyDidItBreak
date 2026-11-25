"""Progress, drafts, active time and run history on top of the local database, plus the Learnings view."""
from __future__ import annotations

import hashlib
import statistics
from datetime import date, datetime, timedelta, timezone

from . import db, problems

MAX_ACTIVITY_REPORT = 30  # seconds; the browser reports every 15 s
MAX_LOG = 500

# What each kind of mistake teaches. The keys are stored in runs.category, so keep them stable.
CATEGORIES: dict[str, tuple[str, str]] = {
    "loop-bounds": ("Off-by-one / loop bounds",
                    "`range(n)` gives 0 … n-1. The last index of a list is `len(x) - 1`; check both ends of every loop."),
    "none-pointer": ("Followed a None pointer",
                     "Guard before you follow a link: `while cur:` / `if node is not None:` before `.next`, `.left`."),
    "missing-key": ("Missing dictionary key",
                    "Use `d.get(k, default)`, `k in d`, or `collections.defaultdict` before reading a key."),
    "empty-pop": ("Took from an empty container",
                  "Check `if stack:` / `if heap:` before `pop()` / `heappop()`."),
    "recursion-base": ("Recursion without a working base case",
                       "Every recursive call must move towards a base case that returns without recursing."),
    "infinite-loop": ("Loop never ended (or far too slow)",
                      "Something in the loop condition has to change on every pass. Look at what never changes."),
    "missing-return": ("Forgot to return",
                       "Every path through the function must end with `return <answer>`."),
    "wrong-length": ("Answer had the wrong number of items",
                     "Count how many items each loop adds, and whether it stops early or runs once too often."),
    "wrong-value": ("Logic computed the wrong value",
                    "Work one small example by hand, then step through and find the first value that differs."),
    "typo": ("Name typo or used before assignment",
             "Read the exact spelling Python complains about; define a variable before you use it."),
    "syntax": ("Syntax error", "Check colons, brackets and indentation on the reported line and the one above it."),
    "type": ("Wrong type of value", "Print or inspect the types involved; a `None` or a list where a number was expected is common."),
    "signature": ("Function name or parameters didn't match",
                  "Keep the `def` line from the starter code exactly as it is."),
    "other": ("Other errors", "Read the error card: it names the line and the values involved."),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today() -> str:
    return date.today().isoformat()


def _valid(problem_id: str) -> bool:
    return problems.by_id(problem_id) is not None


# ---------------------------------------------------------------- categorising

def _from_error(etype: str | None, msg: str = "", viz_kind: str | None = None) -> str:
    if viz_kind == "oob":
        return "loop-bounds"
    if viz_kind == "none":
        return "none-pointer"
    if viz_kind == "missing_key":
        return "missing-key"
    if viz_kind == "empty":
        return "empty-pop"
    if viz_kind == "recursion":
        return "recursion-base"
    if viz_kind == "loop":
        return "infinite-loop"
    return {
        "IndexError": "empty-pop" if "pop" in (msg or "") else "loop-bounds",
        "AttributeError": "none-pointer" if "NoneType" in (msg or "") else "type",
        "KeyError": "missing-key",
        "RecursionError": "recursion-base",
        "StepLimit": "infinite-loop",
        "TimeLimit": "infinite-loop",
        "NameError": "typo",
        "UnboundLocalError": "typo",
        "SyntaxError": "syntax",
        "IndentationError": "syntax",
        "TabError": "syntax",
        "TypeError": "type",
        "MissingFunction": "signature",
    }.get(etype or "", "other")


def _from_why(why: dict | None) -> str:
    if not why:
        return "wrong-value"
    kind = why.get("kind")
    if kind in ("never_written", "too_short"):
        text = " ".join(why.get("detail", []))
        return "loop-bounds" if "range(" in text or "loop" in text else "wrong-length"
    if kind == "too_long":
        return "wrong-length"
    if kind == "no_return":
        return "missing-return"
    return "wrong-value"


def describe_trace(res: dict) -> dict:
    """status / category / title / summary / line for a traced test case."""
    v = res.get("verdict") or {}
    err = res.get("error")
    status = v.get("status", "error" if err else "pass")
    out = {"status": status, "error_type": None, "category": None, "title": None, "summary": None, "line": None}
    if status == "pass":
        return out
    if status == "wrong":
        why = v.get("why")
        out["category"] = _from_why(why)
        out["title"] = "Wrong answer"
        out["summary"] = (why or {}).get("summary") or f"Returned {v.get('got')}, expected {v.get('expected')}."
        out["line"] = (why or {}).get("line")
        return out
    e = err or v.get("error") or {}
    out["error_type"] = e.get("type") or ("TimeLimit" if status == "timeout" else None)
    out["category"] = _from_error(out["error_type"], e.get("msg", ""), (e.get("viz") or {}).get("kind"))
    if status == "timeout" and out["category"] == "other":
        out["category"] = "infinite-loop"
    out["title"] = e.get("title") or e.get("type") or ("Too slow" if status == "timeout" else "Error")
    out["summary"] = e.get("why") or e.get("msg") or ""
    out["line"] = e.get("line")
    return out


def describe_submit(res: dict) -> dict:
    out = {"status": "pass", "error_type": None, "category": None, "title": None, "summary": None, "line": None,
           "passed": res.get("passed", 0), "total": res.get("total", 0)}
    fatal = res.get("fatal")
    if fatal:
        out.update(status="error", error_type=fatal.get("type"), category=_from_error(fatal.get("type")),
                   title=fatal.get("title") or fatal.get("type"), summary=fatal.get("why") or fatal.get("msg"),
                   line=fatal.get("line"))
        return out
    bad = next((r for r in res.get("results", []) if r["status"] not in ("pass", "skipped")), None)
    if not bad:
        return out
    out["status"] = bad["status"]
    if bad["status"] == "wrong":
        out.update(category="wrong-value", title="Wrong answer",
                   summary=f"Test {bad['index'] + 1}: expected {bad.get('expected')}, got {bad.get('got')}.")
    else:
        e = bad.get("error") or {}
        out.update(error_type=e.get("type") or ("TimeLimit" if bad["status"] == "timeout" else None),
                   category="infinite-loop" if bad["status"] == "timeout" else _from_error(e.get("type"), e.get("msg", "")),
                   title=e.get("type") or "Too slow",
                   summary=f"Test {bad['index'] + 1}: " + (f"{e.get('type')}: {e.get('msg')}" if e else "took too long"),
                   line=e.get("line"))
    return out


# ---------------------------------------------------------------- writing

def _touch(conn, problem_id: str):
    conn.execute("INSERT INTO progress (problem_id, first_opened_at) VALUES (?, ?) ON CONFLICT DO NOTHING",
                 (problem_id, _now()))


def record_run(problem_id: str, kind: str, code: str, info: dict, test_index: int | None = None,
               custom_input: str | None = None) -> int | None:
    if not _valid(problem_id):
        return None
    with db.connect() as conn:
        _touch(conn, problem_id)
        active = conn.execute("SELECT active_seconds FROM progress WHERE problem_id = ?", (problem_id,)).fetchone()[0]
        cur = conn.execute(
            """INSERT INTO runs (problem_id, kind, created_at, code, test_index, custom_input, status, passed, total,
                                 error_type, category, title, summary, line, active_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (problem_id, kind, _now(), code, test_index, custom_input, info["status"], info.get("passed"),
             info.get("total"), info.get("error_type"), info.get("category"), info.get("title"),
             (info.get("summary") or "")[:1000] or None, info.get("line"), active))
        if kind == "run":
            conn.execute("UPDATE progress SET runs = runs + 1 WHERE problem_id = ?", (problem_id,))
        elif kind == "submit":
            conn.execute("UPDATE progress SET submits = submits + 1 WHERE problem_id = ?", (problem_id,))
            if info["status"] == "pass":
                conn.execute(
                    """UPDATE progress SET status = 'solved', solved_at = COALESCE(solved_at, ?),
                       seconds_to_solve = COALESCE(seconds_to_solve, active_seconds) WHERE problem_id = ?""",
                    (_now(), problem_id))
        return cur.lastrowid


def add_activity(problem_id: str, seconds: float) -> None:
    secs = int(max(0, min(MAX_ACTIVITY_REPORT, round(seconds))))
    if not secs or not _valid(problem_id):
        return
    with db.connect() as conn:
        _touch(conn, problem_id)
        if conn.execute("SELECT status FROM progress WHERE problem_id = ?", (problem_id,)).fetchone()[0] == "solved":
            return  # the clock stops once a problem is solved
        conn.execute("UPDATE progress SET active_seconds = active_seconds + ? WHERE problem_id = ?", (secs, problem_id))
        conn.execute("""INSERT INTO activity (problem_id, day, seconds) VALUES (?, ?, ?)
                        ON CONFLICT (problem_id, day) DO UPDATE SET seconds = seconds + excluded.seconds""",
                     (problem_id, _today(), secs))


def open_problem(problem_id: str) -> None:
    if _valid(problem_id):
        with db.connect() as conn:
            _touch(conn, problem_id)


def save_draft(problem_id: str, code: str) -> None:
    if not _valid(problem_id):
        return
    with db.connect() as conn:
        conn.execute("""INSERT INTO drafts (problem_id, code, updated_at) VALUES (?, ?, ?)
                        ON CONFLICT (problem_id) DO UPDATE SET code = excluded.code, updated_at = excluded.updated_at""",
                     (problem_id, code, _now()))


def get_draft(problem_id: str) -> str | None:
    with db.connect() as conn:
        row = conn.execute("SELECT code FROM drafts WHERE problem_id = ?", (problem_id,)).fetchone()
    return row["code"] if row else None


def reset(problem_id: str | None = None, drafts: bool = False) -> dict:
    where, args = ("WHERE problem_id = ?", (problem_id,)) if problem_id else ("", ())
    with db.connect() as conn:
        counts = {
            "runs": conn.execute(f"DELETE FROM runs {where}", args).rowcount,
            "progress": conn.execute(f"DELETE FROM progress {where}", args).rowcount,
            "activity": conn.execute(f"DELETE FROM activity {where}", args).rowcount,
        }
        if drafts:
            counts["drafts"] = conn.execute(f"DELETE FROM drafts {where}", args).rowcount
    return counts


def import_local(progress: dict[str, str], drafts: dict[str, str]) -> dict:
    """One-time import of what older versions kept in browser localStorage. Never overwrites database rows."""
    n_p = n_d = 0
    with db.connect() as conn:
        for pid, status in progress.items():
            if _valid(pid) and status in ("tried", "solved"):
                n_p += conn.execute(
                    """INSERT INTO progress (problem_id, status, first_opened_at, solved_at) VALUES (?, ?, ?, ?)
                       ON CONFLICT DO NOTHING""",
                    (pid, status, _now(), _now() if status == "solved" else None)).rowcount
        for pid, code in drafts.items():
            if _valid(pid) and isinstance(code, str) and len(code) <= 50_000:
                n_d += conn.execute("INSERT INTO drafts (problem_id, code, updated_at) VALUES (?, ?, ?) "
                                    "ON CONFLICT DO NOTHING", (pid, code, _now())).rowcount
    return {"progress": n_p, "drafts": n_d}


# ---------------------------------------------------------------- reading

def progress() -> dict:
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM progress").fetchall()
        has_any = conn.execute("SELECT EXISTS (SELECT 1 FROM progress) OR EXISTS (SELECT 1 FROM drafts)").fetchone()[0]
    return {"problems": {r["problem_id"]: dict(r) for r in rows}, "empty": not has_any}


def get_run(run_id: int) -> dict | None:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def _hash(code: str) -> str:
    return hashlib.sha1(code.strip().encode()).hexdigest()


def _mistakes(runs: list[dict]) -> list[dict]:
    """Failed attempts, one per (problem, code): re-running the same code doesn't count twice.
    A traced run's diagnosis is more specific than the submit summary for the same code, so it wins."""
    by_key: dict[tuple, dict] = {}
    for r in runs:
        if r["kind"] == "watch" or r["status"] == "pass" or not r["category"]:
            continue
        key = (r["problem_id"], _hash(r["code"]))
        old = by_key.get(key)
        if old is None or (old["kind"] == "submit" and r["kind"] == "run"):
            by_key[key] = r
    return sorted(by_key.values(), key=lambda r: r["id"])


def learnings() -> dict:
    with db.connect() as conn:
        prog = {r["problem_id"]: dict(r) for r in conn.execute("SELECT * FROM progress")}
        runs = [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY id")]
        days = {r["day"]: r["s"] for r in conn.execute("SELECT day, SUM(seconds) AS s FROM activity GROUP BY day")}
    catalog = problems.catalog()
    titles = {p["id"]: p["title"] for p in catalog}
    levels = {p["id"]: p["level"] for p in catalog}

    # ---- overview
    solved = [p for p in prog.values() if p["status"] == "solved"]
    to_solve = [p["seconds_to_solve"] for p in solved if p["seconds_to_solve"] is not None]
    first_try = 0
    for pid in (p["problem_id"] for p in solved):
        subs = [r for r in runs if r["problem_id"] == pid and r["kind"] == "submit"]
        if subs and subs[0]["status"] == "pass":
            first_try += 1
    active_days = {d for d, s in days.items() if s > 0} | {
        datetime.fromisoformat(r["created_at"]).astimezone().date().isoformat() for r in runs}
    streak, d = 0, date.today()
    if d.isoformat() not in active_days:
        d -= timedelta(days=1)  # an unbroken streak can still be continued today
    while d.isoformat() in active_days:
        streak += 1
        d -= timedelta(days=1)
    today = date.today()
    daily = [{"day": (today - timedelta(days=k)).isoformat(),
              "minutes": round(days.get((today - timedelta(days=k)).isoformat(), 0) / 60, 1)}
             for k in range(29, -1, -1)]
    overview = {
        "total": len(catalog), "solved": len(solved), "attempted": len(prog),
        "active_seconds": sum(p["active_seconds"] for p in prog.values()),
        "median_seconds_to_solve": statistics.median(to_solve) if to_solve else None,
        "first_try": first_try, "streak": streak, "daily": daily,
        "runs": sum(1 for r in runs if r["kind"] == "run"), "submits": sum(1 for r in runs if r["kind"] == "submit"),
    }

    # ---- recurring mistakes
    mistakes = _mistakes(runs)
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    cats: dict[str, dict] = {}
    for m in mistakes:
        c = cats.setdefault(m["category"], {"category": m["category"], "count": 0, "problems": [], "last_at": None,
                                            "examples": []})
        c["count"] += 1
        if m["problem_id"] not in c["problems"]:
            c["problems"].append(m["problem_id"])
        c["last_at"] = m["created_at"]
        c["examples"].append({"run_id": m["id"], "problem_id": m["problem_id"], "summary": m["summary"],
                              "line": m["line"], "created_at": m["created_at"]})
    for c in cats.values():
        c["title"], c["lesson"] = CATEGORIES.get(c["category"], CATEGORIES["other"])
        c["recent"] = (c["last_at"] or "") >= week_ago
        c["examples"] = c["examples"][-5:][::-1]
        c["problems"] = [{"id": p, "title": titles.get(p, p)} for p in c["problems"]]
    ranked = sorted(cats.values(), key=lambda c: (-c["count"], c["category"]))

    # ---- journal
    journal = []
    for pid, p in sorted(prog.items(), key=lambda kv: max([r["id"] for r in runs if r["problem_id"] == kv[0]] or [0]),
                         reverse=True):
        mine = [r for r in runs if r["problem_id"] == pid]
        entry = {
            "problem_id": pid, "title": titles.get(pid, pid), "level": levels.get(pid), "status": p["status"],
            "active_seconds": p["active_seconds"], "seconds_to_solve": p["seconds_to_solve"],
            "runs": p["runs"], "submits": p["submits"], "first_opened_at": p["first_opened_at"],
            "solved_at": p["solved_at"],
            "timeline": [{"id": r["id"], "kind": r["kind"], "status": r["status"], "category": r["category"],
                          "created_at": r["created_at"], "summary": r["summary"]} for r in mine[-60:]],
            "mistakes": sorted({m["category"] for m in mistakes if m["problem_id"] == pid}),
        }
        first_pass = next((r for r in mine if r["kind"] == "submit" and r["status"] == "pass"), None)
        if first_pass:
            before = [r for r in mine if r["id"] < first_pass["id"] and r["kind"] in ("run", "submit")
                      and r["status"] != "pass"]
            if before:
                last_bad = before[-1]
                # prefer the traced diagnosis of that same code
                same = [r for r in before if _hash(r["code"]) == _hash(last_bad["code"]) and r["kind"] == "run"]
                diag = same[-1] if same else last_bad
                entry["fix"] = {"before": last_bad["code"], "after": first_pass["code"],
                                "before_run": last_bad["id"], "after_run": first_pass["id"],
                                "category": diag["category"], "title": diag["title"], "summary": diag["summary"],
                                "line": diag["line"]}
        journal.append(entry)

    log = [{k: r[k] for k in r if k != "code"} | {"title_problem": titles.get(r["problem_id"], r["problem_id"])}
           for r in runs[-MAX_LOG:][::-1]]
    return {"overview": overview, "mistakes": ranked, "journal": journal, "log": log,
            "categories": {k: {"title": t, "lesson": l} for k, (t, l) in CATEGORIES.items()},
            "db_path": str(db.db_path())}
