import pytest

from server import judge, lessons
from server.problems import PROBLEMS, by_id


@pytest.mark.parametrize("problem", PROBLEMS, ids=lambda p: p["id"])
def test_reference_solution_passes_and_starter_does_not(problem):
    assert lessons.by_id(problem["topic"]), "topic must name a lesson (the sample code)"
    res = judge.submit(problem["solution"], problem)
    assert res["passed"] == res["total"] == len(problem["tests"]), res
    starter = judge.submit(problem["starter"], problem)
    assert "fatal" not in starter and starter["passed"] < starter["total"]


def test_known_answers():
    def exp(pid, *args):
        return judge.expected(by_id(pid), list(args))

    assert exp("two-sum", [2, 7, 11, 15], 9) == [0, 1]
    assert exp("reverse-list", [1, 2, 3]) == [3, 2, 1]
    assert exp("invert-tree", [4, 2, 7, 1, 3, 6, 9]) == [4, 7, 2, 9, 6, 3, 1]
    assert exp("coin-change", [1, 3, 4], 6) == 2
    assert exp("num-islands", [[1, 1, 0], [0, 0, 1]]) == 2
    assert exp("network-delay", [[2, 1, 1], [2, 3, 1], [3, 4, 1]], 4, 2) == 2
    assert exp("validate-bst", [5, 4, 6, None, None, 3, 7]) is False
    assert exp("sort-list", [3, 1, 2]) == [1, 2, 3]  # in place: judged on the argument


def _statuses(code, pid):
    return [r["status"] for r in judge.submit(code, by_id(pid))["results"]]


def test_wrong_crash_and_timeout_statuses():
    assert "wrong" in _statuses("def two_sum(nums, target):\n    return [0, 1]\n", "two-sum")
    assert set(_statuses("def two_sum(nums, target):\n    return nums[99]\n", "two-sum")) == {"error"}
    st = _statuses("def two_sum(nums, target):\n    while True:\n        pass\n", "two-sum")
    assert st[0] == "timeout" and "skipped" in st


def test_any_order_is_accepted_but_true_is_not_one():
    assert set(_statuses("def two_sum(nums, target):\n    for i in range(len(nums)):\n"
                         "        for j in range(i):\n            if nums[i] + nums[j] == target:\n"
                         "                return (i, j)\n", "two-sum")) == {"pass"}
    assert "wrong" in _statuses("def is_valid(s):\n    return 1\n", "valid-parentheses")


def test_missing_function_and_syntax_error_are_fatal():
    assert judge.submit("def nope():\n    pass\n", by_id("two-sum"))["fatal"]["type"] == "MissingFunction"
    assert judge.submit("def two_sum(nums, target)\n    pass\n", by_id("two-sum"))["fatal"]["type"] == "SyntaxError"


def test_trace_hides_the_harness_and_marks_the_return():
    p = by_id("reverse-list")
    res = judge.trace(p["solution"], p, [[1, 2, 3]])
    assert res["error"] is None and res["verdict"]["status"] == "pass"
    lines = len(p["solution"].splitlines())
    assert all(1 <= s["line"] <= lines for s in res["steps"])
    assert not any(s["fn"].startswith("__wdib") for s in res["steps"])
    ret = res["steps"][res["return_step"]]
    assert ret["ev"] == "return" and ret["fn"] == "reverse_list"
    # the list nodes built by the harness show up as user objects
    heap = {k: res["pool"][v] for k, v in res["pool"][ret["heap"]].items()}
    assert sum(o["t"] == "obj" and o["cls"] == "ListNode" for o in heap.values()) == 3


def test_trace_crash_gets_forensics_and_wrong_answer_gets_a_diff():
    p = by_id("two-sum")
    crash = judge.trace("def two_sum(nums, target):\n    for i in range(len(nums) + 1):\n"
                        "        if nums[i] == -1:\n            return [i]\n", p, [[3, 2, 4], 6])
    assert crash["verdict"]["status"] == "error"
    assert crash["error"]["type"] == "IndexError" and crash["error"]["viz"]["kind"] == "oob"
    wrong = judge.trace("def sort_list(nums):\n    nums.reverse()\n", by_id("sort-list"), [[3, 1, 2]])
    assert wrong["verdict"]["status"] == "wrong" and "index 0" in wrong["verdict"]["diff"]
    bad_call = judge.trace("def two_sum(nums):\n    pass\n", p, [[3, 2, 4], 6])
    assert bad_call["error"]["driver"] and "parameters" in bad_call["error"]["hint"]


def test_long_but_finishing_run_is_truncated_not_an_error():
    p = by_id("climb-stairs")
    res = judge.trace(p["solution"].replace("range(n)", "range(n * 200)").replace("return a", "return 1346269"),
                      p, [30])
    assert res["error"] is None and res["truncated"] and res["verdict"]["status"] == "pass"


def test_custom_input_parsing():
    p = by_id("two-sum")
    assert judge.parse_custom(p, "[1, 2]\n3") == [[1, 2], 3]
    assert judge.parse_custom(p, "nums = [1, 2]\ntarget = 3") == [[1, 2], 3]
    with pytest.raises(ValueError):
        judge.parse_custom(p, "[1, 2]")
    with pytest.raises(ValueError):
        judge.parse_custom(p, "[1, 2]\nfoo(")
    with pytest.raises(ValueError):  # an input the reference solution can't handle either
        judge.trace(p["solution"], p, [5, 3])


def _why(pid, code, args):
    res = judge.trace(code, by_id(pid), args)
    assert res["verdict"]["status"] == "wrong"
    return res["verdict"]["why"]


def test_why_loop_stops_one_short():
    why = _why("running-sum", "def running_sum(nums):\n    rsum = [0] * len(nums)\n"
               "    for i in range(len(nums)-1):\n        if i > 0:\n            csum = rsum[i-1]\n"
               "        else:\n            csum = 0\n        rsum[i] = csum + nums[i]\n    return rsum\n",
               [[1, 2, 3, 4]])
    assert why["kind"] == "never_written" and why["index"] == 3 and why["var"] == "rsum"
    assert why["line"] == 3  # the loop, where the fix goes
    text = " ".join(why["detail"])
    assert "0, 1, 2" in text and "range(3)" in text


def test_why_wrong_value_written_and_wrong_length():
    why = _why("running-sum", "def running_sum(nums):\n    out = []\n    total = 0\n    for x in nums:\n"
               "        out.append(total)\n        total += x\n    return out\n", [[1, 2, 3, 4]])
    assert why["kind"] == "wrong_write" and why["index"] == 0 and why["line"] == 5
    assert [c["name"] for c in why["culprits"]] == ["total"]
    why = _why("running-sum", "def running_sum(nums):\n    out = []\n    for i in range(1, len(nums)):\n"
               "        out.append(sum(nums[:i + 1]))\n    return out\n", [[1, 2, 3, 4]])
    assert why["kind"] == "too_short" and why["index"] == 3


def test_why_missing_return_and_scalar():
    why = _why("find-index", "def find_index(nums, target):\n    for i in range(len(nums)):\n"
               "        if nums[i] == target:\n            idx = i\n", [[7, 2, 9, 4, 1], 4])
    assert why["kind"] == "no_return"
    why = _why("max-profit", "def max_profit(prices):\n    best = 0\n    for p in prices:\n"
               "        best = max(best, p - prices[0])\n    return best\n", [[7, 1, 5, 3, 6, 4]])
    assert why["kind"] == "wrong_value" and why["culprits"][0]["name"] == "best"
