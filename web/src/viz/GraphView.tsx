import { motion } from "framer-motion";
import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY } from "d3";
import type { Scene } from "../detect";
import type { DictObj, Heap, Val } from "../types";
import { colorFor, deref, label, show, visibleVars } from "../trace";
import { C, type Ctx } from "./common";

interface Edge {
  a: string;
  b: string;
  w?: string;
  both: boolean;
}

const layoutCache = new Map<string, Map<string, { x: number; y: number }>>();
const W = 560;
const H = 300;

function adjacency(obj: DictObj, heap: Heap) {
  const nodes = obj.entries.map(([k]) => label(k, heap));
  const keySet = new Set(nodes);
  const edges = new Map<string, Edge>();
  for (const [k, v] of obj.entries) {
    const a = label(k, heap);
    const o = deref(v, heap);
    if (!o || o.t === "obj") continue;
    const pairs: [string, string | undefined][] = [];
    if (o.t === "dict") for (const [nk, w] of o.entries) pairs.push([label(nk, heap), show(w, heap)]);
    else
      for (const x of o.items) {
        const t = deref(x, heap);
        if (t && t.t === "tuple" && t.items.length === 2) {
          const n0 = label(t.items[0], heap);
          const n1 = label(t.items[1], heap);
          pairs.push(keySet.has(n0) ? [n0, n1] : [n1, n0]);
        } else pairs.push([label(x, heap), undefined]);
      }
    for (const [b, w] of pairs) {
      if (!keySet.has(b)) nodes.push(b), keySet.add(b);
      const rev = edges.get(`${b}->${a}`);
      if (rev && rev.w === w) rev.both = true;
      else edges.set(`${a}->${b}`, { a, b, w, both: false });
    }
  }
  return { nodes, edges: [...edges.values()] };
}

function layout(nodes: string[], edges: Edge[]) {
  const sig = nodes.join("|") + "#" + edges.map((e) => `${e.a}-${e.b}`).join(",");
  const hit = layoutCache.get(sig);
  if (hit) return hit;
  type N = { id: string; x?: number; y?: number };
  const ns: N[] = nodes.map((id, i) => ({
    id,
    x: W / 2 + Math.cos((i / nodes.length) * 2 * Math.PI) * 120,
    y: H / 2 + Math.sin((i / nodes.length) * 2 * Math.PI) * 100,
  }));
  const sim = forceSimulation(ns)
    .force("charge", forceManyBody().strength(-420))
    .force("link", forceLink(edges.map((e) => ({ source: e.a, target: e.b }))).id((d) => (d as N).id).distance(85))
    .force("x", forceX(W / 2).strength(0.06))
    .force("y", forceY(H / 2).strength(0.1))
    .force("collide", forceCollide(32))
    .stop();
  for (let i = 0; i < 300; i++) sim.tick();
  const pos = new Map<string, { x: number; y: number }>();
  for (const n of ns) pos.set(n.id, { x: Math.max(26, Math.min(W - 26, n.x!)), y: Math.max(26, Math.min(H - 26, n.y!)) });
  layoutCache.set(sig, pos);
  return pos;
}

/** Collect labels held by a variable's container (handles tuples like (dist, node)). */
function contents(v: Val, heap: Heap, nodeSet: Set<string>): string[] {
  const o = deref(v, heap);
  if (!o || o.t === "obj") return [];
  const raw = o.t === "dict" ? o.entries.map(([k]) => k) : o.items;
  const out: string[] = [];
  for (const x of raw) {
    const t = deref(x, heap);
    if (t && t.t === "tuple") {
      for (const y of t.items) if (nodeSet.has(label(y, heap))) out.push(label(y, heap));
    } else out.push(label(x, heap));
  }
  return out;
}

export function GraphView({ ctx, scene }: { ctx: Ctx; scene: Scene }) {
  const { heap, frames } = ctx;
  const obj = scene.obj as DictObj;
  const { nodes, edges } = adjacency(obj, heap);
  const nodeSet = new Set(nodes);
  const pos = layout(nodes, edges);

  // derive node states from other variables
  const visited = new Set<string>();
  const frontier = new Set<string>();
  const order = new Map<string, number>();
  const current = new Map<string, string[]>();
  const dist = new Map<string, string>();
  for (const [name, v] of visibleVars(frames)) {
    if (scene.names.includes(name)) continue;
    if (v.t === "ref") {
      const o = heap[v.r];
      if (!o || o.t === "obj") continue;
      const labels = contents(v, heap, nodeSet);
      if (!labels.length || !labels.some((l) => nodeSet.has(l))) continue;
      if (o.t === "set") labels.forEach((l) => visited.add(l));
      else if (o.t === "deque" || /queue|stack|pq|heap|frontier|todo/i.test(name)) labels.forEach((l) => frontier.add(l));
      else if (o.t === "dict") {
        const allKeys = o.entries.every(([k]) => nodeSet.has(label(k, heap)));
        if (allKeys)
          for (const [k, x] of o.entries) {
            const s = show(x, heap);
            if (/^-?[\d.]+$|^inf$/.test(s)) dist.set(label(k, heap), s === "inf" ? "∞" : s);
            else if (/visited|seen/i.test(name)) visited.add(label(k, heap));
          }
      } else if (o.t === "list") {
        if (/visit|seen|done/i.test(name)) labels.forEach((l) => visited.add(l));
        else labels.forEach((l, i) => nodeSet.has(l) && !order.has(l) && order.set(l, i + 1));
      }
    } else if (v.t === "str" || v.t === "int") {
      const l = label(v, heap);
      if (nodeSet.has(l)) current.set(l, [...(current.get(l) ?? []), name]);
    }
  }
  // the edge being explored right now: between two "current" nodes
  const curNodes = [...current.keys()];
  const activeEdge = (e: Edge) => curNodes.includes(e.a) && curNodes.includes(e.b) && e.a !== e.b;

  const ev = ctx.error?.viz;
  const missing = ctx.atError && ev?.kind === "missing_key" && scene.names.includes(ev.var ?? "") ? ev.key?.replace(/^'|'$/g, "") : null;

  return (
    <svg className="viz-svg" viewBox={`0 0 ${W} ${H}`} style={{ maxWidth: W }}>
      <defs>
        <marker id="arrow-g" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill={C.edge} />
        </marker>
        <marker id="arrow-hot" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill={C.cmp} />
        </marker>
      </defs>
      {edges.map((e) => {
        const p = pos.get(e.a);
        const q = pos.get(e.b);
        if (!p || !q) return null;
        const dx = q.x - p.x;
        const dy = q.y - p.y;
        const d = Math.hypot(dx, dy) || 1;
        const r = 22;
        const x1 = p.x + (dx / d) * r;
        const y1 = p.y + (dy / d) * r;
        const x2 = q.x - (dx / d) * r;
        const y2 = q.y - (dy / d) * r;
        const hot = activeEdge(e);
        const ghost = missing && e.b === missing;
        return (
          <g key={`${e.a}->${e.b}`}>
            <motion.line
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke={ghost ? C.bad : hot ? C.cmp : C.edge}
              strokeWidth={hot ? 3 : 1.6}
              strokeDasharray={ghost ? "5 4" : undefined}
              markerEnd={e.both ? undefined : `url(#${hot ? "arrow-hot" : "arrow-g"})`}
              animate={{ opacity: 1 }}
            />
            {e.w && (
              <text x={(p.x + q.x) / 2} y={(p.y + q.y) / 2 - 5} textAnchor="middle" fontSize={11} fill={C.sub}
                fontFamily="var(--mono)" style={{ paintOrder: "stroke" }} stroke={C.panel} strokeWidth={4}>
                {e.w}
              </text>
            )}
          </g>
        );
      })}
      {nodes.map((n) => {
        const p = pos.get(n)!;
        const isCur = current.has(n);
        const isGhost = n === missing;
        const fill = isGhost ? "rgba(244,63,94,.12)" : visited.has(n) ? "rgba(52,211,153,.18)" : "#1b2540";
        const stroke = isGhost ? C.bad : isCur ? colorFor(current.get(n)![0]) : frontier.has(n) ? C.cmp : visited.has(n) ? C.ok : "#4b5b80";
        return (
          <g key={n}>
            {isCur && (
              <motion.circle cx={p.x} cy={p.y} r={26} fill="none" stroke={stroke} strokeWidth={2}
                animate={{ r: [24, 30, 24], opacity: [0.8, 0.2, 0.8] }} transition={{ repeat: Infinity, duration: 1.6 }} />
            )}
            <motion.circle cx={p.x} cy={p.y} r={20} animate={{ fill, stroke }} strokeWidth={isCur ? 3 : 2}
              strokeDasharray={frontier.has(n) && !isCur ? "4 3" : isGhost ? "5 4" : undefined} />
            <text x={p.x} y={p.y + 4.5} textAnchor="middle" fontSize={13} fontWeight={700} fill={C.text}>
              {n}
            </text>
            {dist.has(n) && (
              <text x={p.x} y={p.y + 36} textAnchor="middle" fontSize={11} fill={C.cmp} fontFamily="var(--mono)">
                d={dist.get(n)}
              </text>
            )}
            {order.has(n) && (
              <g transform={`translate(${p.x + 16},${p.y - 18})`}>
                <circle r={8} fill={C.ok} />
                <text y={3.5} textAnchor="middle" fontSize={9} fontWeight={700} fill="#06281c">{order.get(n)}</text>
              </g>
            )}
            {isCur && (
              <text x={p.x} y={p.y - 28} textAnchor="middle" fontSize={11} fontWeight={600} fill={stroke} fontFamily="var(--mono)">
                {current.get(n)!.join(", ")}
              </text>
            )}
            {isGhost && (
              <text x={p.x} y={p.y + 38} textAnchor="middle" fontSize={11} fill={C.bad}>not a key!</text>
            )}
          </g>
        );
      })}
      <g transform={`translate(8, ${H - 10})`} fontSize={10} fill={C.sub}>
        <circle cx={4} cy={-4} r={4} fill="rgba(52,211,153,.4)" stroke={C.ok} />
        <text x={12} y={0}>visited</text>
        <circle cx={66} cy={-4} r={4} fill="none" stroke={C.cmp} strokeDasharray="2 2" />
        <text x={74} y={0}>in queue/stack</text>
        <circle cx={160} cy={-4} r={4} fill="none" stroke={C.read} strokeWidth={2} />
        <text x={168} y={0}>current</text>
      </g>
    </svg>
  );
}
