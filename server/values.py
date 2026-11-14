"""Helpers for the encoded value format produced by runner.Encoder."""
from __future__ import annotations

PRIMS = {"none", "bool", "int", "float", "str", "func", "repr"}


def deref(v, heap):
    if v and v.get("t") == "ref":
        return heap.get(v["r"], {"t": "repr", "v": "?"})
    return v


def is_prim(v) -> bool:
    return v.get("t") in PRIMS


def py(v):
    """Primitive encoded value -> python value (None if not primitive)."""
    t = v.get("t")
    if t == "none":
        return None
    if t in ("bool", "int", "float", "str"):
        return v.get("v")
    return None


def show(v, heap, depth=0) -> str:
    """Short human readable rendering."""
    t = v.get("t")
    if t == "none":
        return "None"
    if t == "str":
        return repr(v["v"])
    if t in ("bool", "int", "float"):
        return str(v["v"])
    if t in ("func", "repr"):
        return str(v.get("v"))
    o = deref(v, heap)
    ot = o.get("t")
    if depth > 1:
        return {"list": "[…]", "tuple": "(…)", "dict": "{…}", "set": "{…}",
                "deque": "deque(…)"}.get(ot, o.get("cls", "…"))
    if ot in ("list", "tuple", "deque", "set"):
        inner = ", ".join(show(x, heap, depth + 1) for x in o["items"][:8])
        if len(o["items"]) > 8 or o.get("more"):
            inner += ", …"
        return {"list": f"[{inner}]", "tuple": f"({inner})", "deque": f"deque([{inner}])",
                "set": "{" + inner + "}" if inner else "set()"}[ot]
    if ot == "dict":
        inner = ", ".join(f"{show(k, heap, depth + 1)}: {show(x, heap, depth + 1)}"
                          for k, x in o["entries"][:6])
        if len(o["entries"]) > 6:
            inner += ", …"
        return "{" + inner + "}"
    if ot == "obj":
        f = o.get("fields", {})
        for key in ("val", "value", "data", "key", "name"):
            if key in f and is_prim(f[key]):
                return f"{o['cls']}({show(f[key], heap, depth + 1)})"
        return o.get("cls", "object")
    return "?"


def same(a, ha, b, hb, depth=0) -> bool:
    """Structural equality of two encoded values from (possibly) different heaps."""
    if a.get("t") != b.get("t"):
        return False
    if a["t"] != "ref":
        return a.get("v") == b.get("v")
    if a["r"] != b["r"]:
        return False
    if depth > 6:
        return True
    oa, ob = ha.get(a["r"], {}), hb.get(b["r"], {})
    if oa.get("t") != ob.get("t"):
        return False
    t = oa.get("t")
    if t in ("list", "tuple", "deque", "set"):
        ia, ib = oa["items"], ob["items"]
        return len(ia) == len(ib) and oa.get("more") == ob.get("more") and all(
            same(x, ha, y, hb, depth + 1) for x, y in zip(ia, ib))
    if t == "dict":
        ea, eb = oa["entries"], ob["entries"]
        return len(ea) == len(eb) and all(
            same(k1, ha, k2, hb, depth + 1) and same(v1, ha, v2, hb, depth + 1)
            for (k1, v1), (k2, v2) in zip(ea, eb))
    if t == "obj":
        fa, fb = oa["fields"], ob["fields"]
        return fa.keys() == fb.keys() and all(
            same(fa[k], ha, fb[k], hb, depth + 1) for k in fa)
    return True


def shallow_same(a, b) -> bool:
    """Identity-level equality: same primitive value or same reference."""
    if a.get("t") != b.get("t"):
        return False
    if a["t"] == "ref":
        return a["r"] == b["r"]
    return a.get("v") == b.get("v")


def frame_by_fid(step, fid):
    for f in step["frames"]:
        if f["fid"] == fid:
            return f
    return None
