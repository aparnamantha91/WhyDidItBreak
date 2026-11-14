import type { Heap, HeapObj, RunResult, Snapshot, Val, Frame } from "./types";

const cache = new WeakMap<RunResult, Map<number, Snapshot>>();

/** Rebuild frames + heap for a step from the deduplicated pool. */
export function snapshot(res: RunResult, i: number): Snapshot {
  let m = cache.get(res);
  if (!m) {
    m = new Map();
    cache.set(res, m);
  }
  const hit = m.get(i);
  if (hit) return hit;
  const s = res.steps[i];
  const pool = res.pool;
  const frames = (pool[s.frames] as number[]).map((fi) => pool[fi] as Frame);
  const hmap = pool[s.heap] as Record<string, number>;
  const heap: Heap = {};
  for (const k in hmap) heap[k] = pool[hmap[k]] as HeapObj;
  const snap = { frames, heap };
  m.set(i, snap);
  return snap;
}

export function deref(v: Val | undefined, heap: Heap): HeapObj | null {
  if (!v || v.t !== "ref") return null;
  return heap[v.r] ?? null;
}

export function isPrim(v: Val | undefined): boolean {
  return !!v && v.t !== "ref";
}

export function num(v: Val | undefined): number | null {
  if (!v) return null;
  if ((v.t === "int" || v.t === "float") && typeof v.v === "number") return v.v;
  if (v.t === "bool") return v.v ? 1 : 0;
  return null;
}

export function show(v: Val | undefined, heap: Heap, depth = 0): string {
  if (!v) return "?";
  switch (v.t) {
    case "none":
      return "None";
    case "str":
      return depth === 0 ? JSON.stringify(v.v).replace(/^"|"$/g, "'") : `'${v.v}'`;
    case "bool":
      return v.v ? "True" : "False";
    case "int":
    case "float":
      return String(v.v);
    case "func":
      return `${v.v}()`;
    case "repr":
      return v.v;
    case "ref": {
      const o = heap[v.r];
      if (!o) return "…";
      if (depth > 1) return o.t === "obj" ? o.cls : o.t === "dict" ? "{…}" : "[…]";
      if (o.t === "obj") {
        for (const k of ["val", "value", "data", "key", "name"]) {
          const f = o.fields[k];
          if (f && isPrim(f)) return `${o.cls}(${show(f, heap, depth + 1)})`;
        }
        return o.cls;
      }
      if (o.t === "dict") {
        const inner = o.entries
          .slice(0, 6)
          .map(([k, x]) => `${show(k, heap, depth + 1)}: ${show(x, heap, depth + 1)}`)
          .join(", ");
        return `{${inner}${o.entries.length > 6 ? ", …" : ""}}`;
      }
      const inner = o.items.slice(0, 8).map((x) => show(x, heap, depth + 1)).join(", ");
      const more = o.items.length > 8 || o.more ? ", …" : "";
      if (o.t === "tuple") return `(${inner}${more})`;
      if (o.t === "set") return inner ? `{${inner}${more}}` : "set()";
      if (o.t === "deque") return `deque([${inner}${more}])`;
      return `[${inner}${more}]`;
    }
  }
}

/** Short label for a value inside a cell (strings without quotes). */
export function label(v: Val | undefined, heap: Heap): string {
  if (v && v.t === "str") return v.v;
  return show(v, heap, 1);
}

/** Variable lookup: top frame first, then globals. */
export function lookup(frames: Frame[], name: string): Val | undefined {
  const top = frames[frames.length - 1];
  return top?.vars[name] ?? frames[0]?.vars[name];
}

/** Visible variables: top frame vars, then globals not shadowed. */
export function visibleVars(frames: Frame[]): [string, Val, boolean][] {
  if (!frames.length) return [];
  const top = frames[frames.length - 1];
  const out: [string, Val, boolean][] = [];
  const seen = new Set<string>();
  for (const [k, v] of Object.entries(top.vars)) {
    if (v.t === "func") continue;
    out.push([k, v, frames.length === 1]);
    seen.add(k);
  }
  if (frames.length > 1) {
    for (const [k, v] of Object.entries(frames[0].vars)) {
      if (seen.has(k) || v.t === "func") continue;
      out.push([k, v, true]);
    }
  }
  return out;
}

const PALETTE = ["#38bdf8", "#f472b6", "#a78bfa", "#34d399", "#fbbf24", "#fb923c", "#22d3ee", "#e879f9"];
const PREFERRED: Record<string, number> = {
  i: 0, j: 1, k: 2, l: 0, lo: 0, left: 0, r: 1, hi: 1, right: 1, mid: 4,
  cur: 0, prev: 1, nxt: 2, slow: 3, fast: 5, head: 2, node: 0, root: 2,
};

export function colorFor(name: string): string {
  if (name in PREFERRED) return PALETTE[PREFERRED[name]];
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return PALETTE[h % PALETTE.length];
}
