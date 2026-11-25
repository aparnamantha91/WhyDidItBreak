import sqlite3

import pytest

from server import db, history, judge
from server.problems import by_id

BUGGY = ("def running_sum(nums):\n    rsum = [0] * len(nums)\n    for i in range(len(nums)-1):\n"
         "        rsum[i] = (rsum[i-1] if i else 0) + nums[i]\n    return rsum\n")
FIXED = BUGGY.replace("len(nums)-1", "len(nums)")


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("WDIB_DATA_DIR", str(tmp_path))
    return tmp_path


def _trace(code, pid="running-sum", test=0):
    p = by_id(pid)
    return judge.trace(code, p, p["tests"][test])


def _attempt(code, pid="running-sum"):
    history.record_run(pid, "run", code, history.describe_trace(_trace(code, pid)), 0)
    history.record_run(pid, "submit", code, history.describe_submit(judge.submit(code, by_id(pid))))


def test_schema_created_outside_repo_and_persists(data_dir):
    assert history.progress() == {"problems": {}, "empty": True}
    history.save_draft("two-sum", "x = 1")
    assert (data_dir / "progress.db").exists()
    with sqlite3.connect(data_dir / "progress.db") as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    assert history.get_draft("two-sum") == "x = 1"  # a fresh connection sees it


def test_migrate_from_older_version(data_dir):
    conn = sqlite3.connect(data_dir / "old.db")
    assert db.migrate(conn) == len(db.MIGRATIONS)
    conn.execute("PRAGMA user_version = 0")
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall():
        conn.execute(f"DROP TABLE {t}")
    assert db.migrate(conn) == len(db.MIGRATIONS)
    assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0


def test_runs_progress_and_time_to_solve():
    history.add_activity("running-sum", 500)  # clamped to 30
    history.add_activity("running-sum", 12)
    _attempt(BUGGY)
    p = history.progress()["problems"]["running-sum"]
    assert p["active_seconds"] == 42 and p["status"] == "tried" and p["runs"] == 1 and p["submits"] == 1
    history.add_activity("running-sum", 20)
    _attempt(FIXED)
    p = history.progress()["problems"]["running-sum"]
    assert p["status"] == "solved" and p["seconds_to_solve"] == 62 and p["solved_at"]
    history.add_activity("running-sum", 5)  # the clock stops once solved
    p = history.progress()["problems"]["running-sum"]
    assert p["seconds_to_solve"] == 62 and p["active_seconds"] == 62


@pytest.mark.parametrize("pid,code,category", [
    ("running-sum", BUGGY, "loop-bounds"),
    ("reverse-list", "def reverse_list(head):\n    cur = head\n    while cur.next:\n        cur = cur.next\n"
                     "    return head\n", "none-pointer"),
    ("find-index", "def find_index(nums, target):\n    for i in range(len(nums)):\n        if nums[i] == target:\n"
                   "            idx = i\n", "missing-return"),
    ("two-sum", "def two_sum(nums, target):\n    while True:\n        pass\n", "infinite-loop"),
    ("two-sum", "def two_sum(nums, target)\n    pass\n", "syntax"),
])
def test_categories(pid, code, category):
    p = by_id(pid)
    tests = p["tests"]
    # pick a test where the bug shows (the empty linked list for the None case)
    t = 2 if pid == "reverse-list" else 0
    info = history.describe_trace(judge.trace(code, p, tests[t]))
    assert info["status"] != "pass" and info["category"] == category, info


def test_learnings_aggregation_and_reset():
    _attempt(BUGGY)
    _attempt(BUGGY)  # the same code again doesn't count as a second mistake
    _attempt(FIXED)
    history.record_run("two-sum", "watch", "x", {"status": "pass", "title": "Watched the solution"})
    L = history.learnings()
    assert L["overview"]["solved"] == 1 and L["overview"]["attempted"] == 2 and L["overview"]["first_try"] == 0
    [m] = L["mistakes"]
    assert m["category"] == "loop-bounds" and m["count"] == 1 and m["recent"]
    entry = next(e for e in L["journal"] if e["problem_id"] == "running-sum")
    assert entry["fix"]["before"] == BUGGY and entry["fix"]["after"] == FIXED
    assert entry["fix"]["category"] == "loop-bounds"
    assert L["overview"]["streak"] == 1 and len(L["log"]) == 7

    history.save_draft("running-sum", FIXED)
    assert history.reset("two-sum")["runs"] == 1
    assert "two-sum" not in history.progress()["problems"]
    assert history.reset(None, drafts=False)["progress"] == 1
    assert history.get_draft("running-sum") == FIXED  # kept
    history.reset(None, drafts=True)
    assert history.progress()["empty"]


def test_import_from_local_storage_never_overwrites():
    _attempt(FIXED)
    out = history.import_local({"running-sum": "tried", "two-sum": "solved", "bogus": "solved"},
                               {"two-sum": "def two_sum(a, b): pass"})
    assert out == {"progress": 1, "drafts": 1}
    rows = history.progress()["problems"]
    assert rows["running-sum"]["status"] == "solved" and rows["two-sum"]["status"] == "solved"


def test_api_records_and_skips_replays():
    from fastapi.testclient import TestClient

    from server.main import app

    c = TestClient(app)
    c.post("/api/run", json={"code": BUGGY, "problem_id": "running-sum", "test": 0})
    c.post("/api/run", json={"code": BUGGY, "problem_id": "running-sum", "test": 0, "watch": "replay"})
    c.post("/api/run", json={"code": "print(1)", "watch": "sample", "watch_problem": "running-sum"})
    c.post("/api/run", json={"code": "print(1)"})  # playground: not recorded
    kinds = [r["kind"] for r in c.get("/api/learnings").json()["log"]]
    assert kinds == ["watch", "run"]
    assert c.put("/api/drafts/running-sum", json={"code": "abc"}).status_code == 200
    assert c.get("/api/drafts/running-sum").json() == {"code": "abc"}
    assert c.delete("/api/progress/running-sum?drafts=true").json()["drafts"] == 1
