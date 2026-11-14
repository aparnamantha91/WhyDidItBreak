import { motion } from "framer-motion";
import type { Scene } from "../detect";
import { pointerNames } from "../detect";
import type { SeqObj } from "../types";
import { label, lookup, num } from "../trace";
import { C, type Ctx, opsFor, PointerTag } from "./common";

const W_MAX = 54;
const H = 150;

/** Bars (numbers) or cells (anything) with index pointers, comparisons and swap arcs. */
export function ArrayView({ ctx, scene }: { ctx: Ctx; scene: Scene }) {
  const obj = scene.obj as SeqObj;
  const items = obj.items;
  const n = items.length;
  const bars = scene.kind === "bars";
  const { frames, heap, step } = ctx;

  // pointers: variables used to index this array
  const ptrs = pointerNames(scene.names, ctx.meta)
    .map((p) => ({ name: p, v: num(lookup(frames, p)) }))
    .filter((p): p is { name: string; v: number } => p.v !== null && Number.isInteger(p.v));

  // highlight accesses on this line
  const acc = (step.acc ?? []).filter((a) => scene.names.includes(a.var) && a.idx.length >= 1);
  const cmpIdx = new Set<number>();
  const readIdx = new Set<number>();
  let ghost: { i: number; expr: string } | null = null;
  for (const a of acc) {
    const v = num(a.idx[0]);
    if (v === null) continue;
    if (a.ok === false && a.idx.length === 1) ghost = { i: v, expr: a.expr[0] };
    const iv = v < 0 ? v + n : v;
    (a.cmp ? cmpIdx : readIdx).add(iv);
  }
  const ev = ctx.error?.viz;
  if (ctx.atError && ev?.kind === "oob" && scene.names.includes(ev.var ?? "") && (ev.depth ?? 0) === 0) {
    ghost = { i: ev.idx ?? n, expr: ev.expr ?? "" };
  }
  const empty = ctx.atError && ev?.kind === "empty" && scene.names.includes(ev.var ?? "");

  // what changed on the way into this step
  const ops = opsFor(step, scene.oid);
  const swap = ops.find((o) => o.k === "swap");
  const setIdx = new Set(ops.filter((o) => o.k === "set").map((o) => o.i!));
  const added = new Set(ops.filter((o) => o.k === "append" || o.k === "insert").map((o) => o.i!));

  // geometry
  let lo = 0;
  let hi = n;
  for (const p of ptrs) {
    lo = Math.min(lo, p.v < -n ? -1 : 0);
    hi = Math.max(hi, p.v >= n ? p.v + 1 : 0);
  }
  if (ghost) {
    if (ghost.i >= n) hi = Math.max(hi, ghost.i + 1);
    if (ghost.i < -n) lo = -1;
  }
  hi = Math.min(hi, n + 3);
  const slots = Math.max(1, hi - lo);
  const width = Math.max(bars ? 240 : 60, Math.min(900, slots * W_MAX));
  const w = width / slots;
  const xOf = (i: number) => (i - lo) * w + w / 2;

  const nums = items.map((x) => num(x) ?? 0);
  const maxAbs = Math.max(1, ...nums.map(Math.abs));
  const hasNeg = nums.some((x) => x < 0);
  const base = bars ? (hasNeg ? H / 2 + 10 : H) : 0;
  const scale = bars ? (hasNeg ? H / 2 - 10 : H - 18) / maxAbs : 0;
  const cellTop = 8;
  const cellH = Math.min(46, w - 6);
  const rowY = bars ? H + 4 : cellTop + cellH + 4;

  // stack pointer tags when several land on the same index
  const tagRow = new Map<number, number>();
  const tagged = ptrs.map((p) => {
    const r = tagRow.get(p.v) ?? 0;
    tagRow.set(p.v, r + 1);
    return { ...p, row: r };
  });
  const tagRows = Math.max(0, ...Array.from(tagRow.values()));
  const svgH = rowY + 22 + tagRows * 30 + 6;

  return (
    <svg className="viz-svg" viewBox={`0 0 ${width} ${svgH}`} style={{ maxWidth: width }}>
      {n === 0 && !ghost && (
        <text x={width / 2} y={rowY - 16} textAnchor="middle" fill={empty ? C.bad : C.sub} fontSize={13}>
          {empty ? "empty — nothing to take!" : "[ ] empty"}
        </text>
      )}
      {items.map((it, i) => {
        const x = xOf(i);
        const isCmp = cmpIdx.has(i);
        const isRead = readIdx.has(i);
        const isSet = setIdx.has(i) || added.has(i);
        const swapped = swap && (swap.i === i || swap.j === i);
        const fill = isCmp ? C.cmp : isSet ? C.write : swapped ? C.ok : isRead ? C.read : C.bar;
        const dx = swapped ? (xOf(swap!.i === i ? swap!.j! : swap!.i!) - x) : 0;
        const v = nums[i];
        const bh = Math.max(2, Math.abs(v) * scale);
        const by = v >= 0 ? base - bh : base;
        const key = swapped || isSet ? `${i}@${ctx.i}` : `${i}`;
        return (
          <motion.g
            key={key}
            initial={swapped ? { x: dx, y: 0 } : added.has(i) ? { opacity: 0, y: -20 } : false}
            animate={swapped ? { x: [dx, dx / 2, 0], y: [0, dx > 0 ? -34 : 34, 0] } : { x: 0, y: 0, opacity: 1 }}
            transition={{ duration: 0.45, ease: "easeInOut" }}
          >
            {bars ? (
              <>
                <motion.rect
                  x={x - w * 0.38}
                  width={w * 0.76}
                  rx={4}
                  animate={{ y: by, height: bh, fill }}
                  transition={{ duration: 0.3 }}
                  style={{ filter: isCmp || swapped ? `drop-shadow(0 0 6px ${fill})` : undefined }}
                />
                <text x={x} y={v >= 0 ? by - 4 : by + bh + 12} textAnchor="middle" fontSize={w < 26 ? 8 : 12}
                  fill={C.text} fontFamily="var(--mono)" fontWeight={600}>
                  {label(it, heap)}
                </text>
              </>
            ) : (
              <>
                <motion.rect
                  x={x - w / 2 + 2}
                  y={cellTop}
                  width={w - 4}
                  height={cellH}
                  rx={6}
                  animate={{ fill: isCmp || isRead || isSet || swapped ? fill : "#1b2540" }}
                  stroke={isCmp || isRead || isSet || swapped ? fill : "#33415f"}
                  strokeWidth={1.5}
                  fillOpacity={isCmp || isRead || isSet || swapped ? 0.28 : 1}
                />
                <text x={x} y={cellTop + cellH / 2 + 4} textAnchor="middle"
                  fontSize={Math.max(8, Math.min(13, (w - 8) / Math.max(1, label(it, heap).length) * 1.6))}
                  fill={C.text} fontFamily="var(--mono)">
                  {label(it, heap)}
                </text>
              </>
            )}
          </motion.g>
        );
      })}
      {obj.more ? (
        <text x={width - 4} y={12} textAnchor="end" fontSize={10} fill={C.sub}>+{obj.more} more</text>
      ) : null}

      {/* ghost slot for out-of-bounds access */}
      {ghost && (
        <g>
          <motion.rect
            x={xOf(ghost.i >= n ? ghost.i : ghost.i < -n ? -1 : ghost.i) - w * 0.42}
            y={bars ? 8 : cellTop}
            width={w * 0.84}
            height={bars ? H - 8 : cellH}
            rx={6}
            fill="rgba(244,63,94,0.08)"
            stroke={C.bad}
            strokeDasharray="5 4"
            strokeWidth={1.5}
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ repeat: Infinity, duration: 1.4 }}
          />
          <text x={xOf(ghost.i >= n ? ghost.i : ghost.i < -n ? -1 : ghost.i)} y={bars ? H / 2 : cellTop + cellH / 2 + 4}
            textAnchor="middle" fontSize={18} fill={C.bad}>
            ?
          </text>
        </g>
      )}

      {/* index row */}
      {items.map((_, i) => (
        <text key={`ix${i}`} x={xOf(i)} y={rowY + 10} textAnchor="middle" fontSize={10} fill={C.dim} fontFamily="var(--mono)">
          {i}
        </text>
      ))}
      {ghost && ghost.i >= n && (
        <text x={xOf(ghost.i)} y={rowY + 10} textAnchor="middle" fontSize={10} fill={C.bad} fontFamily="var(--mono)">
          {ghost.i}
        </text>
      )}

      {/* pointers */}
      {tagged.map((p) => {
        const out = p.v >= n || p.v < -n;
        const pos = p.v < 0 && !out ? p.v + n : out && p.v < 0 ? -1 : p.v;
        return (
          <PointerTag key={p.name} x={xOf(Math.min(pos, hi - 1))} y={rowY + 14 + p.row * 30} name={p.name}
            value={String(p.v)} bad={out} />
        );
      })}
    </svg>
  );
}
