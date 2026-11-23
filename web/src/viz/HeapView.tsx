import { motion } from "framer-motion";
import type { Scene } from "../detect";
import type { SeqObj } from "../types";
import { label, snapshot } from "../trace";
import { C, type Ctx, opsFor } from "./common";

/** Binary heap drawn as a tree (by index) with the backing array underneath. */
export function HeapView({ ctx, scene }: { ctx: Ctx; scene: Scene }) {
  const items = (scene.obj as SeqObj).items;
  const n = items.length;
  const ops = opsFor(ctx.step, scene.oid);
  // heapq rearranges several slots in one call: highlight every slot that differs from the previous step
  const changed = new Set<number>();
  const prevObj = ctx.i > 0 && scene.oid ? (snapshot(ctx.res, ctx.i - 1).heap[scene.oid] as SeqObj | undefined) : undefined;
  if (prevObj && prevObj.items) {
    const prevHeap = snapshot(ctx.res, ctx.i - 1).heap;
    items.forEach((it, i) => {
      const before = prevObj.items[i];
      if (!before || label(before, prevHeap) !== label(it, ctx.heap)) changed.add(i);
    });
  }
  const removed = ops.find((o) => o.k === "pop" || o.k === "popleft");

  const levels = Math.max(1, Math.ceil(Math.log2(n + 1)));
  const width = Math.max(320, Math.min(860, 2 ** (levels - 1) * 64));
  const levelH = 58;
  const pos = (i: number) => {
    const lvl = Math.floor(Math.log2(i + 1));
    const first = 2 ** lvl - 1;
    const slot = i - first;
    const count = 2 ** lvl;
    return { x: ((slot + 0.5) / count) * width, y: 26 + lvl * levelH };
  };
  const treeH = 26 + (levels - 1) * levelH + 30;
  const cw = Math.min(46, width / Math.max(1, n));

  return (
    <div className="heap-wrap">
      <svg className="viz-svg" viewBox={`0 0 ${width} ${treeH + cw + 34}`} style={{ maxWidth: width }}>
        {items.map((_, i) => {
          if (i === 0) return null;
          const p = pos(Math.floor((i - 1) / 2));
          const c = pos(i);
          return <line key={`e${i}`} x1={p.x} y1={p.y} x2={c.x} y2={c.y} stroke={C.edge} strokeWidth={1.5} />;
        })}
        {items.map((it, i) => {
          const { x, y } = pos(i);
          const hot = changed.has(i);
          return (
            <motion.g key={changed.has(i) ? `${i}@${ctx.i}` : `${i}`} initial={changed.has(i) ? { scale: 0.4, opacity: 0 } : false} animate={{ scale: 1, opacity: 1 }}
              style={{ transformOrigin: `${x}px ${y}px` }}>
              <circle cx={x} cy={y} r={19} fill="#1b2540" stroke={i === 0 ? C.ok : hot ? C.write : "#4b5b80"} strokeWidth={2} />
              <text x={x} y={y + 4} textAnchor="middle" fontSize={11} fill={C.text} fontFamily="var(--mono)">
                {label(it, ctx.heap).slice(0, 8)}
              </text>
            </motion.g>
          );
        })}
        {n === 0 && (
          <text x={width / 2} y={40} textAnchor="middle" fill={C.sub} fontSize={13}>
            empty heap
          </text>
        )}
        {/* backing array */}
        <g transform={`translate(${(width - cw * n) / 2}, ${treeH})`}>
          {items.map((it, i) => (
            <g key={`a${i}`}>
              <rect x={i * cw + 1} y={0} width={cw - 2} height={cw - 4} rx={4} fill="#1b2540"
                stroke={i === 0 ? C.ok : "#33415f"} />
              <text x={i * cw + cw / 2} y={cw / 2 + 2} textAnchor="middle" fontSize={10} fill={C.text} fontFamily="var(--mono)">
                {label(it, ctx.heap).slice(0, 7)}
              </text>
              <text x={i * cw + cw / 2} y={cw + 9} textAnchor="middle" fontSize={9} fill={C.dim}>{i}</text>
            </g>
          ))}
        </g>
      </svg>
      {removed && <div className="popped">popped smallest <b>{removed.v}</b></div>}
    </div>
  );
}
