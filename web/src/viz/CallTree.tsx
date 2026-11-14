import { useMemo } from "react";
import { motion } from "framer-motion";
import { hierarchy, tree as d3tree } from "d3";
import type { RunResult } from "../types";
import { show, snapshot } from "../trace";
import { C } from "./common";

interface CallNode {
  id: number; // step index of the call
  fid: string;
  fn: string;
  args: string;
  ret?: string;
  end?: number;
  children: CallNode[];
}

/** Build the call tree from call/return events (all steps, then filtered by time on render). */
function buildCalls(res: RunResult): CallNode | null {
  const root: CallNode = { id: -1, fid: "", fn: "program", args: "", children: [] };
  const stack: CallNode[] = [root];
  // only the user's own functions (skip class bodies and dunder methods like __init__)
  const funcs = new Set((res.meta.funcs ?? []).filter((f) => !f.startsWith("__")));
  const parentOf = () => {
    for (let k = stack.length - 1; k >= 0; k--) if (stack[k].id === -1 || funcs.has(stack[k].fn)) return stack[k];
    return root;
  };
  res.steps.forEach((s, i) => {
    if (s.ev === "call" && s.fn !== "global") {
      const snap = snapshot(res, i);
      const top = snap.frames[snap.frames.length - 1];
      const args = Object.entries(top?.vars ?? {})
        .map(([k, v]) => `${show(v, snap.heap, 1)}`.slice(0, 14) || k)
        .join(", ");
      const node: CallNode = { id: i, fid: s.fid, fn: s.fn, args, children: [] };
      if (funcs.has(s.fn)) parentOf().children.push(node);
      stack.push(node);
    } else if (s.ev === "return" && s.fn !== "global") {
      const node = stack[stack.length - 1];
      if (node && node.fid === s.fid) {
        node.ret = s.ret ? show(s.ret, snapshot(res, i).heap, 1) : "None";
        node.end = i;
        stack.pop();
      }
    }
  });
  return root.children.length ? root : null;
}

const MAX_NODES = 90;

export function CallTree({ res, i, onJump }: { res: RunResult; i: number; onJump: (s: number) => void }) {
  const full = useMemo(() => buildCalls(res), [res]);
  if (!full) return null;

  // prune to calls that have started by step i
  const prune = (n: CallNode): CallNode => ({ ...n, children: n.children.filter((c) => c.id <= i).map(prune) });
  let root = prune(full);
  let count = 0;
  hierarchy(root).each(() => count++);
  let truncated = false;
  if (count > MAX_NODES) {
    // too big (deep recursion): keep only the most recent calls along the active chain
    truncated = true;
    const chain: CallNode[] = [];
    let cur: CallNode | undefined = root;
    while (cur) {
      chain.push(cur);
      cur = cur.children[cur.children.length - 1];
    }
    const tail = chain.slice(-12);
    root = { ...tail[0], children: [] };
    let p = root;
    for (const n of tail.slice(1)) {
      const c = { ...n, children: [] };
      p.children = [c];
      p = c;
    }
  }

  const h = hierarchy(root);
  const nodeW = 92;
  const nodeH = 54;
  d3tree<CallNode>().nodeSize([nodeW, nodeH])(h);
  let minX = Infinity;
  let maxX = -Infinity;
  let maxY = 0;
  h.each((n) => {
    minX = Math.min(minX, n.x!);
    maxX = Math.max(maxX, n.x!);
    maxY = Math.max(maxY, n.y!);
  });
  let currentId = -1;
  h.each((n) => {
    const d = n.data;
    if (d.id <= i && (d.end === undefined || d.end >= i)) currentId = Math.max(currentId, d.id);
  });
  const width = maxX - minX + nodeW + 10;
  const height = maxY + nodeH;
  const ox = -minX + nodeW / 2 + 5;

  return (
    <div className="calltree">
      {truncated && <div className="muted small">showing the 12 most recent nested calls</div>}
      <svg className="viz-svg" viewBox={`0 0 ${width} ${height}`} style={{ width, maxWidth: "none" }}>
        {h.links().map((l) => (
          <line key={`${l.source.data.id}-${l.target.data.id}`} x1={l.source.x! + ox} y1={l.source.y! + 18} x2={l.target.x! + ox}
            y2={l.target.y! + 6} stroke={C.edge} strokeWidth={1.4} />
        ))}
        {h.descendants().map((n) => {
          const d = n.data;
          if (d.id === -1)
            return (
              <text key="root" x={n.x! + ox} y={n.y! + 14} textAnchor="middle" fontSize={10} fill={C.dim}>
                program
              </text>
            );
          const active = d.id <= i && (d.end === undefined || d.end >= i);
          const current = d.id === currentId;
          const done = d.end !== undefined && d.end < i;
          const stroke = current ? C.read : active ? "#6366f1" : done ? C.ok : C.dim;
          const text = `${d.fn}(${d.args})`;
          return (
            <motion.g key={d.id} initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} style={{ cursor: "pointer" }}
              onClick={() => onJump(d.id)}>
              <rect x={n.x! + ox - nodeW / 2 + 4} y={n.y! + 2} width={nodeW - 8} height={20} rx={10}
                fill={current ? "rgba(56,189,248,.18)" : done ? "rgba(52,211,153,.08)" : "#1b2540"} stroke={stroke}
                strokeWidth={current ? 2 : 1.2} />
              <text x={n.x! + ox} y={n.y! + 16} textAnchor="middle" fontSize={10} fill={C.text} fontFamily="var(--mono)">
                {text.length > 13 ? text.slice(0, 12) + "…" : text}
              </text>
              {done && (
                <text x={n.x! + ox} y={n.y! + 34} textAnchor="middle" fontSize={10} fill={C.ok} fontFamily="var(--mono)">
                  ↩ {d.ret!.slice(0, 10)}
                </text>
              )}
            </motion.g>
          );
        })}
      </svg>
    </div>
  );
}
