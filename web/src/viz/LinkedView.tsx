import { motion } from "framer-motion";
import type { Scene } from "../detect";
import { isLinkNode } from "../detect";
import type { UserObj, Val } from "../types";
import { colorFor, label, visibleVars } from "../trace";
import { C, type Ctx } from "./common";

const NW = 78;
const NH = 38;
const GAP = 46;
const ROW = 104;

const POINTERISH = /^(head|tail|cur|curr|current|prev|nxt|next_node|node|slow|fast|p|q|temp|tmp|first|second|dummy|l1|l2|a|b|runner)$/;

function nextOf(o: UserObj): Val | undefined {
  return o.fields.next ?? o.fields.nxt;
}

function valueField(o: UserObj, heap: Parameters<typeof label>[1]): string {
  for (const k of ["val", "value", "data", "key", "item"]) if (o.fields[k]) return label(o.fields[k], heap);
  const first = Object.entries(o.fields).find(([k]) => k !== "next" && k !== "nxt");
  return first ? label(first[1], heap) : "•";
}

/** All linked nodes reachable from variables, laid out as one row per chain. */
export function LinkedView({ ctx }: { ctx: Ctx; scene: Scene }) {
  const { heap, frames } = ctx;
  const vars = visibleVars(frames);

  // discover nodes
  const nodes = new Map<string, UserObj>();
  const stack: string[] = [];
  for (const f of frames) for (const v of Object.values(f.vars)) if (v.t === "ref" && isLinkNode(heap[v.r])) stack.push(v.r);
  while (stack.length) {
    const id = stack.pop()!;
    if (nodes.has(id)) continue;
    const o = heap[id];
    if (!isLinkNode(o)) continue;
    nodes.set(id, o);
    const nx = nextOf(o);
    if (nx && nx.t === "ref") stack.push(nx.r);
  }

  // chains: start at nodes nobody points to
  const incoming = new Set<string>();
  for (const o of nodes.values()) {
    const nx = nextOf(o);
    if (nx && nx.t === "ref" && nodes.has(nx.r)) incoming.add(nx.r);
  }
  const starts = [...nodes.keys()].filter((id) => !incoming.has(id));
  // order chains so the one holding "head" (or the first variable) comes first
  const placed = new Map<string, { x: number; y: number }>();
  const chains: { ids: string[]; tail: Val | undefined; cycleTo?: string }[] = [];
  const walk = (s: string) => {
    const ids: string[] = [];
    let id: string | undefined = s;
    let cycleTo: string | undefined;
    while (id && nodes.has(id)) {
      if (placed.has(id) || ids.includes(id)) {
        cycleTo = id;
        break;
      }
      ids.push(id);
      const nx = nextOf(nodes.get(id)!);
      id = nx && nx.t === "ref" ? nx.r : undefined;
    }
    const last = ids.length ? nextOf(nodes.get(ids[ids.length - 1])!) : undefined;
    chains.push({ ids, tail: cycleTo ? undefined : last, cycleTo });
    ids.forEach((nid, k) => placed.set(nid, { x: 20 + k * (NW + GAP), y: 0 }));
  };
  starts.forEach(walk);
  for (const id of nodes.keys()) if (!placed.has(id)) walk(id); // pure cycles
  chains.forEach((ch, r) => ch.ids.forEach((id) => (placed.get(id)!.y = 34 + r * ROW)));

  // pointer variables
  const ptrs = new Map<string, string[]>();
  const nonePtrs: string[] = [];
  for (const [name, v] of vars) {
    if (v.t === "ref" && nodes.has(v.r)) ptrs.set(v.r, [...(ptrs.get(v.r) ?? []), name]);
    else if (v.t === "none" && POINTERISH.test(name)) nonePtrs.push(name);
  }
  const ev = ctx.error?.viz;
  const noneErr = ctx.atError && ev?.kind === "none" ? ev : null;

  const maxLen = Math.max(1, ...chains.map((c) => c.ids.length));
  const width = Math.max(360, 40 + maxLen * (NW + GAP) + 70);
  const height = 34 + chains.length * ROW + (nonePtrs.length ? 34 : 0);

  return (
    <svg className="viz-svg" viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: width }}>
      <defs>
        <marker id="arrow-l" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="#7c8db5" />
        </marker>
      </defs>
      {chains.map((ch) =>
        ch.ids.map((id, k) => {
          const p = placed.get(id)!;
          const isLast = k === ch.ids.length - 1;
          const x1 = p.x + NW - 12;
          const y1 = p.y + NH / 2;
          if (!isLast) {
            return (
              <motion.line key={`a${id}`} initial={false} animate={{ x1, y1, x2: x1 + GAP + 12, y2: y1 }}
                stroke="#7c8db5" strokeWidth={2} markerEnd="url(#arrow-l)" />
            );
          }
          if (ch.cycleTo) {
            const t = placed.get(ch.cycleTo)!;
            const d = `M${x1},${y1} C${x1 + 60},${y1 + 60} ${t.x + NW / 2},${t.y + NH + 60} ${t.x + NW / 2},${t.y + NH + 2}`;
            return (
              <g key={`a${id}`}>
                <path d={d} fill="none" stroke={C.bad} strokeWidth={2} markerEnd="url(#arrow-l)" strokeDasharray="5 3" />
                <text x={x1 + 40} y={y1 + 52} fill={C.bad} fontSize={11}>cycle!</text>
              </g>
            );
          }
          const target = ch.tail && ch.tail.t === "ref" ? placed.get(ch.tail.r) : undefined;
          if (target) {
            const d = `M${x1},${y1} C${x1 + 50},${y1} ${target.x - 50},${target.y + NH / 2} ${target.x},${target.y + NH / 2}`;
            return <path key={`a${id}`} d={d} fill="none" stroke="#7c8db5" strokeWidth={2} markerEnd="url(#arrow-l)" />;
          }
          const isBadNone = noneErr && (ptrs.get(id) ?? []).some((n) => noneErr.expr?.startsWith(n));
          return (
            <g key={`a${id}`}>
              <line x1={x1} y1={y1} x2={x1 + 34} y2={y1} stroke="#7c8db5" strokeWidth={2} markerEnd="url(#arrow-l)" />
              <motion.text x={x1 + 40} y={y1 + 4} fontSize={12} fontFamily="var(--mono)"
                fill={isBadNone ? C.bad : C.dim}
                animate={isBadNone ? { opacity: [0.4, 1, 0.4] } : {}}
                transition={{ repeat: Infinity, duration: 1.2 }}>
                None
              </motion.text>
            </g>
          );
        }),
      )}
      {[...placed.entries()].map(([id, p]) => {
        const o = nodes.get(id)!;
        const names = ptrs.get(id) ?? [];
        const col = names.length ? colorFor(names[0]) : "#4b5b80";
        const changed = ctx.step.ops.some((op) => op.oid === id && op.k === "field");
        return (
          <motion.g key={id} initial={false} animate={{ x: p.x, y: p.y }} transition={{ type: "spring", stiffness: 160, damping: 20 }}>
            <rect width={NW} height={NH} rx={8} fill="#1b2540" stroke={changed ? C.write : col} strokeWidth={names.length || changed ? 2.2 : 1.4}
              style={{ filter: changed ? `drop-shadow(0 0 6px ${C.write})` : undefined }} />
            <line x1={NW - 22} y1={0} x2={NW - 22} y2={NH} stroke="#33415f" />
            <text x={(NW - 22) / 2} y={NH / 2 + 5} textAnchor="middle" fontSize={14} fontWeight={700} fill={C.text} fontFamily="var(--mono)">
              {valueField(o, heap)}
            </text>
            <circle cx={NW - 11} cy={NH / 2} r={3} fill="#7c8db5" />
            {names.map((n, k) => (
              <text key={n} x={NW / 2} y={-8 - k * 13} textAnchor="middle" fontSize={11} fontWeight={700} fill={colorFor(n)} fontFamily="var(--mono)">
                {n}
                {k === 0 ? " ↓" : ""}
              </text>
            ))}
          </motion.g>
        );
      })}
      {nonePtrs.length > 0 && (
        <g transform={`translate(20, ${height - 16})`}>
          {nonePtrs.map((n, k) => {
            const bad = noneErr && noneErr.expr?.split(".")[0] === n;
            return (
              <motion.text key={n} x={k * 110} y={0} fontSize={12} fontFamily="var(--mono)" fontWeight={600}
                fill={bad ? C.bad : colorFor(n)}
                animate={bad ? { opacity: [0.4, 1, 0.4] } : {}} transition={{ repeat: Infinity, duration: 1.2 }}>
                {n} → None{bad ? "  💥" : ""}
              </motion.text>
            );
          })}
        </g>
      )}
    </svg>
  );
}
