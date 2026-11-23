import type { Frame, Heap, HeapObj, Meta, SeqObj, UserObj, Val } from "./types";
import { deref, isPrim, label, visibleVars } from "./trace";

export type SceneKind =
  | "bars"
  | "cells"
  | "grid"
  | "stack"
  | "queue"
  | "heap"
  | "hash"
  | "graph"
  | "linked"
  | "tree"
  | "object";

export interface Scene {
  kind: SceneKind;
  key: string;
  names: string[]; // variables that refer to this structure
  oid?: string;
  obj?: HeapObj;
}

const LINK_FIELDS = ["next", "nxt"];
const TREE_FIELDS = ["left", "right", "children"];

export const KIND_LABEL: Record<SceneKind, string> = {
  bars: "Array (bars)",
  cells: "Array (cells)",
  grid: "2D grid",
  stack: "Stack",
  queue: "Queue",
  heap: "Heap",
  hash: "Hash map",
  graph: "Graph",
  linked: "Linked list",
  tree: "Tree",
  object: "Object",
};

/** Which renderers make sense for a given structure (for the per-variable override menu). */
export function alternatives(obj: HeapObj): SceneKind[] {
  if (obj.t === "dict") return ["hash", "graph"];
  if (obj.t === "set") return ["hash"];
  if (obj.t === "obj") return ["object"];
  const prims = obj.items.every(isPrim);
  return prims ? ["bars", "cells", "stack", "queue", "heap"] : ["cells", "grid", "stack", "queue"];
}

function isNumeric(v: Val) {
  return (v.t === "int" || v.t === "float") && typeof v.v === "number";
}

export function isLinkNode(o: HeapObj | null | undefined): o is UserObj {
  return !!o && o.t === "obj" && LINK_FIELDS.some((f) => f in o.fields) && !TREE_FIELDS.some((f) => f in o.fields);
}

export function isTreeNode(o: HeapObj | null | undefined): o is UserObj {
  return !!o && o.t === "obj" && TREE_FIELDS.some((f) => f in o.fields);
}

function looksLikeGraph(obj: HeapObj, heap: Heap): boolean {
  if (obj.t !== "dict" || obj.entries.length < 2) return false;
  const keys = new Set(obj.entries.map(([k]) => label(k, heap)));
  let total = 0;
  let hits = 0;
  for (const [, v] of obj.entries) {
    const o = deref(v, heap);
    if (!o) return false;
    let nbrs: Val[];
    if (o.t === "dict") nbrs = o.entries.map(([k]) => k);
    else if (o.t === "obj") return false;
    else nbrs = o.items.map((x) => {
      const t = deref(x, heap);
      // weighted edge as (node, w) or (w, node) tuple
      if (t && t.t === "tuple" && t.items.length === 2) {
        const a = label(t.items[0], heap);
        return keys.has(a) ? t.items[0] : t.items[1];
      }
      return x;
    });
    for (const n of nbrs) {
      total++;
      if (keys.has(label(n, heap))) hits++;
    }
  }
  return total === 0 ? obj.entries.length >= 2 && obj.entries.every(([, v]) => {
    const o = deref(v, heap);
    return o && o.t !== "obj" && (o.t === "dict" ? o.entries.length === 0 : o.items.length === 0);
  }) : hits / total >= 0.6;
}

export function classify(name: string, obj: HeapObj, heap: Heap, meta: Meta): SceneKind {
  const role = meta.roles?.[name];
  if (obj.t === "obj") {
    if (isLinkNode(obj)) return "linked";
    if (isTreeNode(obj)) return "tree";
    return "object";
  }
  if (obj.t === "set") return "hash";
  if (obj.t === "dict") return looksLikeGraph(obj, heap) ? "graph" : "hash";
  const seq = obj as SeqObj;
  if (role === "heap") return "heap";
  if (role === "stack") return "stack";
  if (role === "queue" || seq.t === "deque") return "queue";
  if (seq.items.length > 0 && seq.items.every(isNumeric)) return "bars";
  if (
    seq.t === "list" &&
    seq.items.length > 0 &&
    seq.items.every((x) => {
      const o = deref(x, heap);
      return o && o.t === "list" && o.items.every(isPrim);
    })
  ) {
    const rows = seq.items.map((x) => (deref(x, heap) as SeqObj).items.length);
    if (seq.items.length >= 2 || rows[0] >= 2) return "grid";
  }
  return "cells";
}

/**
 * Turn the visible variables of a snapshot into a list of scenes to draw.
 * Linked-list and tree nodes are merged into one scene each so that all the
 * pointer variables (head, cur, prev…) appear on the same picture.
 */
export function detectScenes(
  frames: Frame[],
  heap: Heap,
  meta: Meta,
  overrides: Record<string, SceneKind>,
): Scene[] {
  const scenes: Scene[] = [];
  const byOid = new Map<string, Scene>();
  let linked: Scene | null = null;
  let tree: Scene | null = null;

  for (const [name, v] of visibleVars(frames)) {
    if (v.t !== "ref") continue;
    const obj = heap[v.r];
    if (!obj) continue;
    const existing = byOid.get(v.r);
    if (existing) {
      existing.names.push(name);
      continue;
    }
    let kind = overrides[name] ?? classify(name, obj, heap, meta);
    if (!alternatives(obj).includes(kind) && kind !== "linked" && kind !== "tree") {
      kind = classify(name, obj, heap, meta);
    }
    if (kind === "linked") {
      if (!linked) {
        linked = { kind, key: "linked", names: [] };
        scenes.push(linked);
      }
      linked.names.push(name);
      continue;
    }
    if (kind === "tree") {
      if (!tree) {
        tree = { kind, key: "tree", names: [] };
        scenes.push(tree);
      }
      tree.names.push(name);
      continue;
    }
    const sc: Scene = { kind, key: `${kind}:${v.r}`, names: [name], oid: v.r, obj };
    byOid.set(v.r, sc);
    scenes.push(sc);
  }

  // nodes held only by outer frames (e.g. the global root while recursing) still deserve a picture
  if (!tree || !linked) {
    for (const f of frames)
      for (const v of Object.values(f.vars)) {
        if (v.t !== "ref") continue;
        const o = heap[v.r];
        if (!tree && isTreeNode(o)) {
          tree = { kind: "tree", key: "tree", names: [] };
          scenes.push(tree);
        } else if (!linked && isLinkNode(o)) {
          linked = { kind: "linked", key: "linked", names: [] };
          scenes.push(linked);
        }
      }
  }

  // the "main" structures first: a graph or tree matters more than the helper lists around it
  const rank: Record<SceneKind, number> = {
    graph: 0, tree: 1, linked: 2, grid: 3, bars: 4, heap: 5, stack: 6, queue: 6, cells: 7, hash: 8, object: 9,
  };
  return scenes
    .map((s, k) => [s, k] as const)
    .sort((a, b) => rank[a[0].kind] - rank[b[0].kind] || a[1] - b[1])
    .map(([s]) => s);
}

/** Index-like variables that point into `names` (from static analysis of subscripts). */
export function pointerNames(names: string[], meta: Meta): string[] {
  const out: string[] = [];
  for (const n of names) for (const p of meta.index_vars?.[n] ?? []) if (!out.includes(p)) out.push(p);
  return out;
}
