"""Turns raw state diffs into operations + plain-English narration per step."""
from __future__ import annotations

from .values import deref, frame_by_fid, is_prim, shallow_same, show

MAX_OPS = 8


def _var_names_for(step, oid):
    """Variables (top frame first) that reference heap object oid directly."""
    names = []
    for f in reversed(step["frames"]):
        for k, v in f["vars"].items():
            if v.get("t") == "ref" and v["r"] == oid and k not in names:
                names.append(k)
    return names


def _name_of(step, oid):
    names = _var_names_for(step, oid)
    if names:
        return names[0]
    heap = step["heap"]
    # one level up: parent container held by a variable
    for pid, obj in heap.items():
        t = obj.get("t")
        if t in ("list", "tuple", "deque"):
            for i, x in enumerate(obj["items"]):
                if x.get("t") == "ref" and x["r"] == oid:
                    pn = _var_names_for(step, pid)
                    if pn:
                        return f"{pn[0]}[{i}]"
        elif t == "obj":
            for fk, x in obj["fields"].items():
                if x.get("t") == "ref" and x["r"] == oid:
                    pn = _var_names_for(step, pid)
                    if pn:
                        return f"{pn[0]}.{fk}"
        elif t == "dict":
            for k, x in obj["entries"]:
                if x.get("t") == "ref" and x["r"] == oid:
                    pn = _var_names_for(step, pid)
                    if pn:
                        return f"{pn[0]}[{show(k, heap)}]"
    return show({"t": "ref", "r": oid}, heap)


def _diff_seq(name, oid, a, b, ha, hb, role):
    ia, ib = a["items"], b["items"]
    na, nb = len(ia), len(ib)
    ops = []
    if na == nb:
        diffs = [i for i in range(na) if not shallow_same(ia[i], ib[i])]
        if len(diffs) == 2:
            i, j = diffs
            if shallow_same(ia[i], ib[j]) and shallow_same(ia[j], ib[i]):
                return [{"k": "swap", "var": name, "oid": oid, "i": i, "j": j,
                         "a": show(ia[i], ha), "b": show(ia[j], ha)}]
        for i in diffs[:4]:
            ops.append({"k": "set", "var": name, "oid": oid, "i": i,
                        "old": show(ia[i], ha), "v": show(ib[i], hb)})
        return ops
    if nb == na + 1:
        if all(shallow_same(x, y) for x, y in zip(ia, ib)):
            return [{"k": "append", "var": name, "oid": oid, "i": nb - 1, "v": show(ib[-1], hb),
                     "role": role}]
        if all(shallow_same(x, y) for x, y in zip(ia, ib[1:])):
            return [{"k": "insert", "var": name, "oid": oid, "i": 0, "v": show(ib[0], hb), "role": role}]
        for p in range(nb):
            if all(shallow_same(x, y) for x, y in zip(ia[:p], ib[:p])) and all(
                    shallow_same(x, y) for x, y in zip(ia[p:], ib[p + 1:])):
                return [{"k": "insert", "var": name, "oid": oid, "i": p, "v": show(ib[p], hb),
                         "role": role}]
    if nb == na - 1:
        if all(shallow_same(x, y) for x, y in zip(ia, ib)):
            return [{"k": "pop", "var": name, "oid": oid, "i": na - 1, "v": show(ia[-1], ha), "role": role}]
        if all(shallow_same(x, y) for x, y in zip(ia[1:], ib)):
            return [{"k": "popleft", "var": name, "oid": oid, "i": 0, "v": show(ia[0], ha), "role": role}]
        for p in range(na):
            if all(shallow_same(x, y) for x, y in zip(ia[:p], ib[:p])) and all(
                    shallow_same(x, y) for x, y in zip(ia[p + 1:], ib[p:])):
                return [{"k": "remove", "var": name, "oid": oid, "i": p, "v": show(ia[p], ha),
                         "role": role}]
    return [{"k": "resize", "var": name, "oid": oid, "from": na, "to": nb}]


def _diff_obj(prev, cur, roles):
    ha, hb = prev["heap"], cur["heap"]
    ops = []
    for oid, b in hb.items():
        a = ha.get(oid)
        if not a or a.get("t") != b.get("t"):
            continue
        t = b["t"]
        if t in ("list", "deque", "tuple", "set"):
            if len(a["items"]) == len(b["items"]) and all(
                    shallow_same(x, y) for x, y in zip(a["items"], b["items"])):
                continue
            name = _name_of(cur, oid)
            if t == "set":
                sa = {show(x, ha) for x in a["items"]}
                sb = {show(x, hb) for x in b["items"]}
                for x in sorted(sb - sa):
                    ops.append({"k": "add", "var": name, "oid": oid, "v": x})
                for x in sorted(sa - sb):
                    ops.append({"k": "discard", "var": name, "oid": oid, "v": x})
                continue
            base = name.split("[")[0].split(".")[0]
            ops.extend(_diff_seq(name, oid, a, b, ha, hb, roles.get(base)))
        elif t == "dict":
            ma = {show(k, ha): v for k, v in a["entries"]}
            mb = {show(k, hb): v for k, v in b["entries"]}
            name = None
            for k, v in mb.items():
                if k not in ma:
                    name = name or _name_of(cur, oid)
                    ops.append({"k": "dset", "var": name, "oid": oid, "key": k, "v": show(v, hb), "new": True})
                elif not shallow_same(ma[k], v):
                    name = name or _name_of(cur, oid)
                    ops.append({"k": "dset", "var": name, "oid": oid, "key": k, "v": show(v, hb),
                                "old": show(ma[k], ha)})
            for k in ma:
                if k not in mb:
                    name = name or _name_of(cur, oid)
                    ops.append({"k": "ddel", "var": name, "oid": oid, "key": k})
        elif t == "obj":
            for f, v in b["fields"].items():
                old = a["fields"].get(f)
                if old is None or not shallow_same(old, v):
                    ops.append({"k": "field", "var": _name_of(cur, oid), "oid": oid, "f": f,
                                "v": show(v, hb), "old": show(old, ha) if old else None})
    return ops


def _diff_vars(prev, cur):
    ops = []
    for f in cur["frames"]:
        pf = frame_by_fid(prev, f["fid"])
        if pf is None:
            continue
        for k, v in f["vars"].items():
            old = pf["vars"].get(k)
            if old is None:
                ops.append({"k": "new", "var": k, "v": show(v, cur["heap"]), "fid": f["fid"]})
            elif not shallow_same(old, v):
                ops.append({"k": "assign", "var": k, "v": show(v, cur["heap"]),
                            "old": show(old, prev["heap"]), "fid": f["fid"]})
    return ops


def _say(op) -> str:
    k = op["k"]
    var = op.get("var")
    role = op.get("role")
    if k == "swap":
        return f"Swapped {var}[{op['i']}] ↔ {var}[{op['j']}]  ({op['a']} ↔ {op['b']})"
    if k == "set":
        return f"{var}[{op['i']}] changed {op['old']} → {op['v']}"
    if k == "append":
        return f"Pushed {op['v']} onto {var}" if role == "stack" else \
            f"Enqueued {op['v']} into {var}" if role == "queue" else f"Appended {op['v']} to {var}"
    if k == "insert":
        return f"Inserted {op['v']} into {var} at index {op['i']}"
    if k == "pop":
        return f"Popped {op['v']} off {var}" if role != "heap" else f"Removed {op['v']} from heap {var}"
    if k == "popleft":
        return f"Dequeued {op['v']} from the front of {var}" if role != "heap" else \
            f"Popped smallest ({op['v']}) from heap {var}"
    if k == "remove":
        return f"Removed {op['v']} from {var} (index {op['i']})"
    if k == "resize":
        return f"{var} changed size {op['from']} → {op['to']}"
    if k == "add":
        return f"Added {op['v']} to set {var}"
    if k == "discard":
        return f"Removed {op['v']} from set {var}"
    if k == "dset":
        if op.get("new"):
            return f"{var}[{op['key']}] = {op['v']}  (new key)"
        return f"{var}[{op['key']}] updated {op['old']} → {op['v']}"
    if k == "ddel":
        return f"Deleted key {op['key']} from {var}"
    if k == "field":
        return f"{var}.{op['f']} now → {op['v']}"
    if k == "new":
        return f"Created {var} = {op['v']}"
    if k == "assign":
        return f"{var}: {op['old']} → {op['v']}"
    return ""


def _element(step, var, idx):
    """Value of var[idx0][idx1]... in the current top frame, as a display string."""
    top = step["frames"][-1] if step["frames"] else None
    if not top:
        return None
    v = top["vars"].get(var)
    if v is None and step["frames"]:
        v = step["frames"][0]["vars"].get(var)
    if v is None:
        return None
    heap = step["heap"]
    for i in idx:
        o = deref(v, heap)
        ii = i.get("v")
        if o.get("t") in ("list", "tuple", "deque") and isinstance(ii, int):
            items = o["items"]
            if -len(items) <= ii < len(items):
                v = items[ii]
            else:
                return None
        elif o.get("t") == "dict":
            found = None
            for k, x in o["entries"]:
                if is_prim(k) and k.get("v") == ii:
                    found = x
            if found is None:
                return None
            v = found
        else:
            return None
    return show(v, heap)


def annotate(steps: list[dict], meta: dict) -> None:
    roles = meta.get("roles", {})
    cmp_lines = set(meta.get("compare_lines", []))
    cnt = {"steps": 0, "cmp": 0, "swaps": 0, "writes": 0, "calls": 0}
    for k, cur in enumerate(steps):
        did: list[str] = []
        ops: list[dict] = []
        if k > 0:
            prev = steps[k - 1]
            if prev["ev"] == "return":
                did.append(f"{prev['fn']}() returned {show(prev['ret'], prev['heap'])}")
            heap_ops = _diff_obj(prev, cur, roles)
            var_ops = _diff_vars(prev, cur)
            ops = heap_ops + var_ops
            did.extend(s for s in (_say(o) for o in ops[:MAX_OPS]) if s)
        if cur["ev"] == "call":
            cnt["calls"] += 1
            top = cur["frames"][-1] if cur["frames"] else {"vars": {}}
            args = ", ".join(f"{a}={show(v, cur['heap'])}" for a, v in top["vars"].items())
            did.append(f"Called {cur['fn']}({args})")
        if cur["ev"] == "exception":
            did.append(f"💥 {cur['exc']['type']}: {cur['exc']['msg']}")
        if cur["ev"] == "line":
            cnt["steps"] += 1
            if cur["line"] in cmp_lines:
                cnt["cmp"] += 1
        for o in ops:
            if o["k"] == "swap":
                cnt["swaps"] += 1
            elif o["k"] in ("set", "append", "insert", "pop", "popleft", "remove", "dset", "ddel",
                            "add", "discard", "field"):
                cnt["writes"] += 1

        nxt = None
        acc = cur.get("acc") or []
        cmp_acc = [a for a in acc if a.get("cmp")]
        if cmp_acc:
            parts = []
            for a in cmp_acc[:3]:
                val = _element(cur, a["var"], a["idx"])
                parts.append(f"{a['text']}={val}" if val is not None else f"{a['text']} (out of range!)")
            nxt = "Comparing " + " vs ".join(parts)
        elif acc:
            bad = [a for a in acc if a.get("ok") is False]
            if bad:
                nxt = f"About to access {bad[0]['text']} — that's outside {bad[0]['var']}!"

        cur["ops"] = ops
        cur["did"] = did
        cur["next"] = nxt
        cur["cnt"] = dict(cnt)
