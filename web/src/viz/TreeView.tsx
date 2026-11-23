import { motion } from "framer-motion";
import { hierarchy, tree as d3tree } from "d3";
import type { Scene } from "../detect";
import { isTreeNode } from "../detect";
import type { Heap, UserObj, Val } from "../types";
import { colorFor, deref, label, visibleVars } from "../trace";
import { C, type Ctx } from "./common";

interface TNode {
  id: string; // heap oid or placeholder
  obj?: UserObj;
  children: TNode[];
  side?: "L" | "R";
}

function keyOf(o: UserObj, heap: Heap) {
  for (const k of ["key", "val", "value", "data", "name"]) if (o.fields[k]) return label(o.fields[k], heap);
  return o.cls;
}

function kids(o: UserObj, heap: Heap): (Val | null)[] {
  if (o.fields.children) {
    const c = deref(o.fields.children, heap);
    return c && c.t !== "obj" && c.t !== "dict" ? c.items : [];
  }
  return [o.fields.left ?? null, o.fields.right ?? null];
}

/** Every tree reachable from variables, laid out with d3.tree; pointer vars ride on the nodes. */
export function TreeView({ ctx }: { ctx: Ctx; scene: Scene }) {
  const { heap, frames } = ctx;
  const vars = visibleVars(frames);

  const all = new Map<string, UserObj>();
  const childOf = new Set<string>();
  const todo: string[] = [];
  // discover from every frame (recursive calls shadow the global root)
  for (const f of frames) for (const v of Object.values(f.vars)) if (v.t === "ref" && isTreeNode(heap[v.r])) todo.push(v.r);
  while (todo.length) {
    const id = todo.pop()!;
    if (all.has(id)) continue;
    const o = heap[id];
    if (!isTreeNode(o)) continue;
    all.set(id, o);
    for (const c of kids(o, heap)) if (c && c.t === "ref") (childOf.add(c.r), todo.push(c.r));
  }
  const roots = [...all.keys()].filter((id) => !childOf.has(id));

  const build = (id: string, seen: Set<string>): TNode => {
    const o = all.get(id)!;
    seen.add(id);
    const binary = !o.fields.children;
    const cs = kids(o, heap);
    const children: TNode[] = [];
    const real = cs.filter((c) => c && c.t === "ref" && all.has(c.r) && !seen.has(c.r));
    cs.forEach((c, k) => {
      if (c && c.t === "ref" && all.has(c.r) && !seen.has(c.r)) {
        const n = build(c.r, seen);
        n.side = binary ? (k === 0 ? "L" : "R") : undefined;
        children.push(n);
      } else if (binary && real.length === 1) {
        children.push({ id: `${id}-ph${k}`, children: [], side: k === 0 ? "L" : "R" });
      }
    });
    return { id, obj: o, children };
  };

  const ptrs = new Map<string, string[]>();
  for (const [name, v] of vars) if (v.t === "ref" && all.has(v.r)) ptrs.set(v.r, [...(ptrs.get(v.r) ?? []), name]);

  // nodes whose key already appears in an output list (e.g. in-order traversal result) are "done"
  const done = new Set<string>();
  for (const [, v] of vars) {
    const o = deref(v, heap);
    if (o && o.t === "list" && o.items.every((x) => x.t !== "ref")) o.items.forEach((x) => done.add(label(x, heap)));
  }

  const ev = ctx.error?.viz;
  const noneErr = ctx.atError && ev?.kind === "none" ? ev : null;

  const nodeW = 52;
  const levelH = 64;
  let offsetX = 0;
  const laid: { id: string; x: number; y: number; obj?: UserObj; side?: string }[] = [];
  const links: { id: string; x1: number; y1: number; x2: number; y2: number; ph: boolean }[] = [];
  let maxY = 0;
  const seen = new Set<string>();
  for (const r of roots) {
    const h = hierarchy(build(r, seen));
    d3tree<TNode>().nodeSize([nodeW, levelH])(h);
    let minX = Infinity;
    let maxX = -Infinity;
    h.each((n) => {
      minX = Math.min(minX, n.x!);
      maxX = Math.max(maxX, n.x!);
    });
    const dx = offsetX - minX + 30;
    h.each((n) => {
      const x = n.x! + dx;
      const y = n.y! + 40;
      maxY = Math.max(maxY, y);
      laid.push({ id: n.data.id, x, y, obj: n.data.obj, side: n.data.side });
      if (n.parent) links.push({ id: n.data.id, x1: n.parent.x! + dx, y1: n.parent.y! + 40, x2: x, y2: y, ph: !n.data.obj });
    });
    offsetX += maxX - minX + nodeW + 40;
  }
  const width = Math.max(360, offsetX + 20);
  const height = maxY + 50;

  return (
    <svg className="viz-svg" viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: Math.max(width, 360) }}>
      {links.map((l) => (
        <motion.line key={`l${l.id}`} initial={false} animate={{ x1: l.x1, y1: l.y1, x2: l.x2, y2: l.y2 }}
          stroke={l.ph ? "transparent" : C.edge} strokeWidth={1.8} />
      ))}
      {laid.map((n) => {
        if (!n.obj) {
          return (
            <text key={n.id} x={n.x} y={n.y + 4} textAnchor="middle" fontSize={11} fill="#334155" fontFamily="var(--mono)">
              ∅
            </text>
          );
        }
        const names = ptrs.get(n.id) ?? [];
        const col = names.length ? colorFor(names[0]) : done.has(keyOf(n.obj, heap)) ? C.ok : "#4b5b80";
        const changed = ctx.step.ops.some((o) => o.oid === n.id && o.k === "field");
        return (
          <motion.g key={n.id} initial={{ x: n.x, y: n.y - 20, opacity: 0 }} animate={{ x: n.x, y: n.y, opacity: 1 }}
            transition={{ type: "spring", stiffness: 170, damping: 20 }}>
            {names.length > 0 && (
              <motion.circle r={25} fill="none" stroke={col} strokeWidth={1.5}
                animate={{ opacity: [0.7, 0.15, 0.7] }} transition={{ repeat: Infinity, duration: 1.6 }} />
            )}
            <circle r={19} fill={done.has(keyOf(n.obj, heap)) ? "rgba(52,211,153,.18)" : "#1b2540"}
              stroke={changed ? C.write : col} strokeWidth={names.length || changed ? 2.5 : 1.6} />
            <text y={4.5} textAnchor="middle" fontSize={13} fontWeight={700} fill={C.text} fontFamily="var(--mono)">
              {keyOf(n.obj, heap).slice(0, 5)}
            </text>
            {names.length > 0 && (
              <text y={-28} textAnchor="middle" fontSize={11} fontWeight={700} fill={col} fontFamily="var(--mono)">
                {names.join(", ")}
              </text>
            )}
          </motion.g>
        );
      })}
      {noneErr && (
        <motion.text x={width / 2} y={height - 12} textAnchor="middle" fill={C.bad} fontSize={12} fontFamily="var(--mono)"
          animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.2 }}>
          {noneErr.expr} → None 💥
        </motion.text>
      )}
    </svg>
  );
}
