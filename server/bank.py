"""The company-wise problem bank.

Company lists (title, difficulty, topics and how often each company asks it) come from
github.com/liquidslr/leetcode-company-wise-problems and are stored in the local database
only. Each unique problem then gets an original write-up (statement, tests, reference
solution) authored for WhyDidItBreak, validated by running it, and stored next to it.

    python -m server.bank sync               download the lists, add new problems and company tags
    python -m server.bank next [--n 25]      write the next batch of problems to author
    python -m server.bank import FILE...     validate authored specs and store the good ones
    python -m server.bank status             counts by status
"""
from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from . import db

SOURCE_ZIP = "https://codeload.github.com/liquidslr/leetcode-company-wise-problems/zip/refs/heads/main"
SOURCE_NAME = "liquidslr/leetcode-company-wise-problems"
LEVEL = {"EASY": "Beginner", "MEDIUM": "Intermediate", "HARD": "Advanced"}
WINDOWS = {  # file name in each company folder -> window key
    "1. Thirty Days.csv": "30d",
    "2. Three Months.csv": "3m",
    "3. Six Months.csv": "6m",
    "4. More Than Six Months.csv": "older",
    "5. All.csv": "all",
}
# problems that can't be judged as "call a Python function, compare the result"
SKIP_TOPICS = {
    "Database": "SQL problem",
    "Shell": "shell problem",
    "Concurrency": "concurrency problem",
    "Interactive": "interactive problem",
    "Design": "class-design problem",
    "Iterator": "class-design problem",
    "Data Stream": "class-design problem",
}
# LeetCode topic -> the closest lesson in lessons.py (first match wins)
LESSON_FOR = [
    ("Union Find", "union-find"), ("Shortest Path", "dijkstra"), ("Backtracking", "backtracking"),
    ("Heap (Priority Queue)", "heap"), ("Linked List", "linked-list"), ("Binary Search Tree", "bst"),
    ("Binary Tree", "bst"), ("Tree", "bst"), ("Breadth-First Search", "bfs"), ("Depth-First Search", "dfs"),
    ("Graph", "dfs"), ("Dynamic Programming", "dp-memo"), ("Sliding Window", "sliding-window"),
    ("Two Pointers", "two-pointers"), ("Binary Search", "binary-search"), ("Monotonic Stack", "stack"),
    ("Stack", "stack"), ("Queue", "queue"), ("Hash Table", "hashmap"), ("Recursion", "recursion"),
    ("Divide and Conquer", "merge-sort"), ("Sorting", "merge-sort"),
]
MIN_TESTS = 6
# problems with no topic tags are almost all JavaScript / pandas exercises; these few are real algorithms
KEEP_UNTAGGED = {"maximum-team-size-with-overlapping-intervals", "find-root-of-a-colored-tree"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def work_dir() -> Path:
    d = db.data_dir() / "bank"
    d.mkdir(parents=True, exist_ok=True)
    return d


def lesson_for(topics: list[str], difficulty: str = "") -> str | None:
    for t, lesson in LESSON_FOR:
        if t in topics:
            if lesson == "dp-memo" and "Matrix" in topics:
                return "dp-grid"
            return lesson
    return "loops" if difficulty == "EASY" else None


# ---------------------------------------------------------------- sync

def slug_of(link: str) -> str:
    return link.rstrip("/").split("/problems/", 1)[-1].split("/", 1)[0]


def parse_csv(text: str) -> list[dict]:
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        link = (r.get("Link") or "").strip()
        title = (r.get("Title") or "").strip()
        if not link or not title:
            continue
        try:
            freq = float(r.get("Frequency") or 0)
        except ValueError:
            freq = 0.0
        rows.append({
            "slug": slug_of(link), "title": title, "difficulty": (r.get("Difficulty") or "").strip().upper(),
            "frequency": freq, "topics": [t.strip() for t in (r.get("Topics") or "").split(",") if t.strip()],
        })
    return rows


def read_zip(data: bytes) -> dict[tuple[str, str], list[dict]]:
    """{(company, window): rows} from the repo archive."""
    out = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            parts = name.split("/")
            if len(parts) != 3 or parts[2] not in WINDOWS:
                continue
            out[(parts[1], WINDOWS[parts[2]])] = parse_csv(z.read(name).decode("utf-8", "replace"))
    return out


def download() -> bytes:
    req = urllib.request.Request(SOURCE_ZIP, headers={"User-Agent": "whydidbreak-bank/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    (work_dir() / "source.zip").write_bytes(data)
    return data


def sync(lists: dict[tuple[str, str], list[dict]]) -> dict:
    """Add new problems and company tags. Never touches authored specs."""
    from . import problems  # late: problems looks the bank up too

    builtin = {p["lc"] for p in problems.PROBLEMS if p.get("lc")}
    seen: dict[str, dict] = {}
    tags = []
    for (company, window), rows in lists.items():
        for r in rows:
            if r["difficulty"] not in LEVEL:
                continue
            seen.setdefault(r["slug"], r)
            tags.append((r["slug"], company, window, r["frequency"]))
    added = 0
    now = _now()
    with db.connect() as conn:
        have = {r[0] for r in conn.execute("SELECT id FROM bank_problems")}
        for slug, r in seen.items():
            if slug in have:
                continue
            skip = next((why for t, why in SKIP_TOPICS.items() if t in r["topics"]), None)
            if not r["topics"] and slug not in KEEP_UNTAGGED:  # LeetCode's JavaScript / pandas tracks
                skip = "JavaScript or pandas exercise"
            status = "builtin" if slug in builtin else "skipped" if skip else "pending"
            conn.execute(
                "INSERT INTO bank_problems (id, title, difficulty, level, topics, status, skip_reason, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (slug, r["title"], r["difficulty"], LEVEL[r["difficulty"]], json.dumps(r["topics"]), status,
                 skip, now))
            added += 1
        if builtin:  # a built-in problem covers it: tag the built-in instead of authoring a duplicate
            conn.execute("UPDATE bank_problems SET status = 'builtin' WHERE id IN (%s)" % ",".join("?" * len(builtin)),
                         tuple(builtin))
        conn.executemany(
            "INSERT INTO bank_companies (problem_id, company, window, frequency) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (problem_id, company, window) DO UPDATE SET frequency = excluded.frequency", tags)
    return {"problems": len(seen), "added": added, "companies": len({c for c, _ in lists}), "tags": len(tags)}


# ---------------------------------------------------------------- authoring

def next_batch(n: int = 25, exclude: set[str] = frozenset()) -> list[dict]:
    """Most-asked pending problems first."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT p.id, p.title, p.difficulty, p.topics, p.last_error,"
            " (SELECT COUNT(DISTINCT company) FROM bank_companies c WHERE c.problem_id = p.id) AS asked_by"
            " FROM bank_problems p WHERE p.status = 'pending' ORDER BY asked_by DESC, p.id").fetchall()
    out = []
    for r in rows:
        if r["id"] in exclude:
            continue
        item = {"id": r["id"], "title": r["title"], "difficulty": r["difficulty"], "topics": json.loads(r["topics"])}
        if r["last_error"]:
            item["previous_attempt_failed"] = r["last_error"]
        out.append(item)
        if len(out) >= n:
            break
    return out


SPEC_KEYS = ("fn", "params", "statement", "solution", "tests", "visible", "constraints", "hints", "explain",
             "compare", "output", "kinds", "ret", "returns")


def build(meta: dict, raw: dict) -> dict:
    """The P() dict for an authored spec, with the bank's own title / level / topic."""
    from .problems import P

    kw = {k: raw[k] for k in SPEC_KEYS[5:] if raw.get(k) is not None}
    topics = json.loads(meta["topics"]) if isinstance(meta["topics"], str) else meta["topics"]
    spec = P(meta["id"], meta["title"], LEVEL[meta["difficulty"]], lesson_for(topics, meta["difficulty"]),
             raw["fn"], raw["params"], raw["statement"], raw["solution"], raw["tests"], **kw)
    spec["difficulty"] = meta["difficulty"]
    spec["topics"] = topics
    spec["bank"] = True
    return spec


def validate(spec: dict) -> str | None:
    """None if the spec is good, else what's wrong with it."""
    from . import judge

    fn, params, tests = spec["fn"], spec["params"], spec["tests"]
    if not isinstance(fn, str) or not fn.isidentifier():
        return f"bad function name {fn!r}"
    if not isinstance(params, list) or not all(isinstance(p, str) and p.isidentifier() for p in params):
        return "params must be a list of identifiers"
    if not isinstance(tests, list) or len(tests) < MIN_TESTS:
        return f"needs at least {MIN_TESTS} tests"
    for i, t in enumerate(tests):
        if not isinstance(t, list) or len(t) != len(params):
            return f"test {i + 1} must be a list with one value per parameter ({len(params)})"
    if not isinstance(spec["statement"], str) or len(spec["statement"]) < 20:
        return "statement is missing"
    if spec.get("compare") not in ("exact", "unordered", "unordered2", "float"):
        return f"unknown compare mode {spec.get('compare')!r}"
    if spec.get("output") not in ("return", "arg0"):
        return f"unknown output mode {spec.get('output')!r}"
    for k in list((spec.get("kinds") or {}).values()) + [spec.get("ret")]:
        if k not in (None, "linked", "tree"):
            return f"unknown kind {k!r}"
    for code, what in ((spec["solution"], "solution"), (spec["starter"], "starter")):
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"{what} has a syntax error: {e}"
        if what == "solution" and not any(isinstance(n, ast.FunctionDef) and n.name == fn for n in tree.body):
            return f"solution doesn't define {fn}()"
    if len({repr(t) for t in tests}) != len(tests):
        return "tests contain duplicates"
    res = judge._run_cases(spec["solution"], spec, tests)
    if "syntax" in res:
        return f"solution: {res['syntax'].get('msg')}"
    for i, case in enumerate(res["cases"]):
        if case["status"] != "ok":
            why = (case.get("error") or {}).get("msg") or case["status"]
            return f"reference solution fails test {i + 1}: {why}"
        if not judge._value(case["result"])[0]:
            return f"test {i + 1}: the answer isn't a plain Python value"
    return None


def _preview(spec: dict) -> list[str]:
    """The visible examples with the answers the reference solution gives, to check `explain` against."""
    from . import judge

    # run the spec itself: it may not be committed yet, so judge.expected() (which looks it up by id) can't
    shown = spec["tests"][:spec.get("visible", 3)]
    cases = judge._run_cases(spec["solution"], spec, shown).get("cases", [])
    out = []
    for i, (args, case) in enumerate(zip(shown, cases)):
        note = spec["explain"][i] if i < len(spec.get("explain", [])) else ""
        got = judge._value(case.get("result"))[1] if case.get("status") == "ok" else case.get("status")
        out.append(f"{judge.show_input(spec, args)} -> {got!r}" + (f"   # {note}" if note else ""))
    return out


def import_specs(items: list[dict], preview: dict | None = None) -> dict:
    counts = {"ready": 0, "skipped": 0, "failed": 0, "unknown": 0}
    errors = {}
    with db.connect() as conn:
        metas = {r["id"]: dict(r) for r in conn.execute("SELECT id, title, difficulty, topics, status FROM bank_problems")}
    for raw in items:
        pid = raw.get("id")
        meta = metas.get(pid)
        if not meta or meta["status"] == "builtin":
            counts["unknown"] += 1
            continue
        if raw.get("skip"):
            with db.connect() as conn:
                conn.execute("UPDATE bank_problems SET status = 'skipped', skip_reason = ?, spec = NULL, updated_at = ?"
                             " WHERE id = ?", (str(raw["skip"])[:300], _now(), pid))
            counts["skipped"] += 1
            continue
        try:
            spec = build(meta, raw)
            err = validate(spec)
        except Exception as e:  # malformed spec
            err = f"{type(e).__name__}: {e}"
        with db.connect() as conn:
            if err:
                conn.execute("UPDATE bank_problems SET last_error = ?, updated_at = ? WHERE id = ?",
                             (err[:500], _now(), pid))
                counts["failed"] += 1
                errors[pid] = err
            else:
                conn.execute("UPDATE bank_problems SET status = 'ready', spec = ?, last_error = NULL, updated_at = ?"
                             " WHERE id = ?", (json.dumps(spec), _now(), pid))
                counts["ready"] += 1
        if preview is not None and not err:
            preview[pid] = _preview(spec)
    if errors:
        counts["errors"] = errors
    return counts


def status() -> dict:
    with db.connect() as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS n FROM bank_problems GROUP BY status").fetchall()
        companies = conn.execute("SELECT COUNT(DISTINCT company) FROM bank_companies").fetchone()[0]
    return {**{r["status"]: r["n"] for r in rows}, "companies": companies}


# ---------------------------------------------------------------- reading (used by the server)

def spec(problem_id: str) -> dict | None:
    with db.connect() as conn:
        r = conn.execute("SELECT spec FROM bank_problems WHERE id = ? AND status = 'ready'", (problem_id,)).fetchone()
    return json.loads(r["spec"]) if r else None


def catalog() -> list[dict]:
    """Light rows for every ready bank problem, most-asked first."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT p.id, p.title, p.level, p.difficulty, p.topics,"
            " (SELECT COUNT(DISTINCT company) FROM bank_companies c WHERE c.problem_id = p.id) AS asked_by"
            " FROM bank_problems p WHERE p.status = 'ready' ORDER BY asked_by DESC, p.title").fetchall()
    out = []
    for r in rows:
        topics = json.loads(r["topics"])
        out.append({"id": r["id"], "title": r["title"], "level": r["level"], "difficulty": r["difficulty"],
                    "topics": topics, "topic": lesson_for(topics, r["difficulty"])})
    return out


def company_tags() -> dict[str, list[str]]:
    """{leetcode slug: companies that ever asked it}"""
    out: dict[str, list[str]] = {}
    with db.connect() as conn:
        for r in conn.execute("SELECT DISTINCT problem_id, company FROM bank_companies ORDER BY company"):
            out.setdefault(r["problem_id"], []).append(r["company"])
    return out


def companies() -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT company, GROUP_CONCAT(DISTINCT window) AS windows FROM bank_companies GROUP BY company"
            " ORDER BY company COLLATE NOCASE").fetchall()
    return [{"name": r["company"], "windows": sorted(r["windows"].split(","), key=list(WINDOWS.values()).index)}
            for r in rows]


def company_frequency(company: str, window: str) -> dict[str, float]:
    """{leetcode slug: frequency} for one company and time window."""
    with db.connect() as conn:
        rows = conn.execute("SELECT problem_id, frequency FROM bank_companies WHERE company = ? AND window = ?",
                            (company, window)).fetchall()
    return {r["problem_id"]: r["frequency"] or 0 for r in rows}


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m server.bank")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync")
    s.add_argument("--zip", help="use a downloaded copy of the repo archive instead of fetching it")
    n = sub.add_parser("next")
    n.add_argument("--n", type=int, default=25)
    n.add_argument("--batches", type=int, default=1, help="write this many batch files")
    i = sub.add_parser("import")
    i.add_argument("files", nargs="+")
    sub.add_parser("status")
    a = ap.parse_args(argv)

    if a.cmd == "sync":
        data = Path(a.zip).read_bytes() if a.zip else download()
        print(json.dumps(sync(read_zip(data)), indent=1))
    elif a.cmd == "next":
        taken: set[str] = set()
        for _ in range(a.batches):
            batch = next_batch(a.n, taken)
            if not batch:
                break
            taken |= {b["id"] for b in batch}
            k = 1 + max([int(p.stem.split("-")[1]) for p in work_dir().glob("todo-*.json")] or [0])
            path = work_dir() / f"todo-{k:04d}.json"
            path.write_text(json.dumps(batch, indent=1))
            print(path)
    elif a.cmd == "import":
        items = []
        for f in a.files:
            data = json.loads(Path(f).read_text())
            items.extend(data if isinstance(data, list) else [data])
        preview: dict = {}
        res = import_specs(items, preview)
        if preview:
            res["preview"] = preview
        print(json.dumps(res, indent=1))
    elif a.cmd == "status":
        print(json.dumps(status(), indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
