import io
import zipfile

import pytest

from server import bank, problems

HEADER = "Difficulty,Title,Frequency,Acceptance Rate,Link,Topics\n"


def _csv(*rows):
    return HEADER + "".join(rows)


ROW_TWO_SUM = 'EASY,Two Sum,100.0,0.5,https://leetcode.com/problems/two-sum,"Array, Hash Table"\n'
ROW_PLUS_ONE = 'EASY,Plus One,40.0,0.4,https://leetcode.com/problems/plus-one/,"Array, Math"\n'
ROW_SQL = "EASY,Big Countries,30.0,0.7,https://leetcode.com/problems/big-countries,Database\n"
ROW_LRU = 'MEDIUM,LRU Cache,90.0,0.4,https://leetcode.com/problems/lru-cache,"Hash Table, Design"\n'


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(f"repo-main/{name}", text)
        z.writestr("repo-main/README.md", "hi")
    return buf.getvalue()


LISTS = bank.read_zip(_zip({
    "Google/5. All.csv": _csv(ROW_TWO_SUM, ROW_PLUS_ONE, ROW_SQL),
    "Google/1. Thirty Days.csv": _csv(ROW_PLUS_ONE),
    "Meta/5. All.csv": _csv(ROW_PLUS_ONE, ROW_LRU),
}))

PLUS_ONE = {
    "id": "plus-one", "fn": "plus_one", "params": ["digits"],
    "statement": "A number is stored as a list of its decimal digits. Return the digits of that number plus one.",
    "solution": "def plus_one(digits):\n    n = int(''.join(map(str, digits))) + 1\n    return [int(c) for c in str(n)]\n",
    "tests": [[[1, 2, 3]], [[9]], [[9, 9]], [[0]], [[4, 3, 2, 1]], [[1, 9, 9]]],
}


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("WDIB_DATA_DIR", str(tmp_path))
    return tmp_path


def test_parse_and_windows():
    assert set(LISTS) == {("Google", "all"), ("Google", "30d"), ("Meta", "all")}
    two = LISTS[("Google", "all")][0]
    assert two == {"slug": "two-sum", "title": "Two Sum", "difficulty": "EASY", "frequency": 100.0,
                   "topics": ["Array", "Hash Table"]}
    assert LISTS[("Google", "all")][1]["slug"] == "plus-one"  # trailing slash in the link


def test_sync_dedupes_skips_and_marks_builtins():
    r = bank.sync(LISTS)
    assert r["problems"] == 4 and r["added"] == 4 and r["companies"] == 2
    s = bank.status()
    assert s == {"builtin": 1, "pending": 1, "skipped": 2, "companies": 2}
    assert [b["id"] for b in bank.next_batch()] == ["plus-one"]
    assert bank.company_tags()["plus-one"] == ["Google", "Meta"]
    assert bank.company_frequency("Google", "30d") == {"plus-one": 40.0}
    assert bank.companies() == [{"name": "Google", "windows": ["30d", "all"]}, {"name": "Meta", "windows": ["all"]}]


def test_import_validates_and_serves():
    bank.sync(LISTS)
    assert problems.by_id("plus-one") is None  # not authored yet
    assert bank.import_specs([PLUS_ONE])["ready"] == 1
    p = problems.by_id("plus-one")
    assert p["level"] == "Beginner" and p["fn"] == "plus_one" and p["topic"] == "loops"
    assert "def plus_one(digits):" in p["starter"]
    row = next(r for r in problems.catalog() if r["id"] == "plus-one")
    assert row["companies"] == ["Google", "Meta"] and not row["builtin"]
    two = next(r for r in problems.catalog() if r["id"] == "two-sum")  # the built-in one, tagged
    assert two["builtin"] and two["companies"] == ["Google"]
    assert sum(r["title"] == "Two Sum" for r in problems.catalog()) == 1


def test_sync_again_keeps_authored_specs():
    bank.sync(LISTS)
    bank.import_specs([PLUS_ONE])
    assert bank.sync(LISTS)["added"] == 0
    assert problems.by_id("plus-one") is not None


@pytest.mark.parametrize("change, why", [
    ({"tests": PLUS_ONE["tests"][:3]}, "at least"),
    ({"solution": "def plus_one(digits):\n    return digits[5]\n"}, "fails test"),
    ({"solution": "def other(digits):\n    return 1\n"}, "doesn't define"),
    ({"tests": [[1, 2]] * 6}, "one value per parameter"),
    ({"compare": "fuzzy"}, "compare"),
])
def test_import_rejects_bad_specs(change, why):
    bank.sync(LISTS)
    res = bank.import_specs([{**PLUS_ONE, **change}])
    assert res["failed"] == 1 and why in res["errors"]["plus-one"]
    assert problems.by_id("plus-one") is None
    assert "previous_attempt_failed" in bank.next_batch()[0]


def test_skip_and_builtin_are_not_overwritten():
    bank.sync(LISTS)
    res = bank.import_specs([{"id": "plus-one", "skip": "needs a class"}, {**PLUS_ONE, "id": "two-sum"}])
    assert res["skipped"] == 1 and res["unknown"] == 1
    assert bank.next_batch() == []


def test_first_import_with_preview():
    bank.sync(LISTS)
    preview = {}
    assert bank.import_specs([{**PLUS_ONE, "explain": ["123 + 1"]}], preview)["ready"] == 1
    assert preview["plus-one"][0] == "digits = [1, 2, 3] -> [1, 2, 4]   # 123 + 1"


def test_export_then_load_into_fresh_db(tmp_path, monkeypatch):
    bank.sync(LISTS)
    bank.import_specs([PLUS_ONE])
    with bank.db.connect() as c:
        c.execute("UPDATE bank_problems SET status = 'skipped', skip_reason = 'x' WHERE id = 'big-countries'")
    seed = tmp_path / "seed.jsonl"
    assert bank.export(seed) == 3  # plus-one ready; big-countries and lru-cache skipped
    monkeypatch.setenv("WDIB_DATA_DIR", str(tmp_path / "fresh"))  # a new machine: empty database, no sync
    assert problems.by_id("plus-one") is None
    assert bank.load_seed(seed) == 3
    assert problems.by_id("plus-one")["fn"] == "plus_one"
    assert bank.load_seed(seed) == 0  # nothing left to do
    assert bank.status()["skipped"] == 2
