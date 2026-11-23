import pytest

from server.lessons import LESSONS
from server.tracer import run


def rehydrate(res, i):
    s = res["steps"][i]
    pool = res["pool"]
    frames = [pool[f] for f in pool[s["frames"]]]
    heap = {k: pool[v] for k, v in pool[s["heap"]].items()}
    return frames, heap


def test_bubble_sort_swaps_and_compares():
    res = run("a=[3,1,2]\nfor i in range(2):\n    for j in range(2-i):\n        if a[j] > a[j+1]:\n"
              "            a[j],a[j+1]=a[j+1],a[j]\nprint(a)\n")
    assert res["error"] is None
    assert res["stdout"] == "[1, 2, 3]\n"
    assert any(o["k"] == "swap" for s in res["steps"] for o in s["ops"])
    assert res["steps"][-1]["cnt"]["swaps"] == 2
    assert any(s["next"] and s["next"].startswith("Comparing") for s in res["steps"])


def test_linked_list_heap_objects():
    res = run("class N:\n    def __init__(s,v,n=None):\n        s.val=v; s.next=n\nh=N(1,N(2))\n")
    frames, heap = rehydrate(res, len(res["steps"]) - 1)
    objs = [o for o in heap.values() if o["t"] == "obj"]
    assert {o["fields"]["val"]["v"] for o in objs} == {1, 2}


def test_recursion_call_events():
    res = run("def f(n):\n    return 1 if n<=1 else n*f(n-1)\nprint(f(4))\n")
    assert res["stdout"] == "24\n"
    assert sum(1 for s in res["steps"] if s["ev"] == "call" and s["fn"] == "f") == 4


@pytest.mark.parametrize("code,etype,kind", [
    ("a=[1,2]\nfor i in range(3):\n    a[i]\n", "IndexError", "oob"),
    ("d={}\nd['x']+=1\n", "KeyError", "missing_key"),
    ("x=None\nx.val\n", "AttributeError", "none"),
    ("def f(n):\n    return f(n-1)\nf(3)\n", "RecursionError", "recursion"),
    ("i=0\nwhile i<3:\n    pass\n", "StepLimit", "loop"),
    ("s=[]\ns.pop()\n", "IndexError", "empty"),
])
def test_error_forensics(code, etype, kind):
    err = run(code)["error"]
    assert err["type"] == etype
    assert err["viz"]["kind"] == kind
    assert err["why"] and err["hint"]


def test_syntax_error():
    err = run("if True\n  print(1)\n")["error"]
    assert err["type"] == "SyntaxError" and err["line"] == 1 and "colon" in err["hint"]


def test_name_error_suggestion():
    err = run("total=1\nprint(totl)\n")["error"]
    assert "total" in err["hint"]


def test_culprit_history():
    err = run("a=[1,2,3]\ni=0\nwhile True:\n    a[i]\n    i+=1\n")["error"]
    c = err["culprits"][0]
    assert c["name"] == "i" and c["value"] == "3"
    assert [h["v"] for h in c["history"]][-2:] == ["2", "3"]


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda l: l["id"])
def test_lessons(lesson):
    assert run(lesson["code"])["error"] is None
    bad = run(lesson["buggy"])
    assert bad["error"] is not None or bad["stdout"] != run(lesson["code"])["stdout"]
