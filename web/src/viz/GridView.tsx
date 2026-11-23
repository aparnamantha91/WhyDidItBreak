import { Fragment } from "react";
import { motion } from "framer-motion";
import type { Scene } from "../detect";
import type { SeqObj } from "../types";
import { deref, label, num } from "../trace";
import { C, type Ctx } from "./common";

/** 2D list as a heatmap table (DP tables, grids, matrices). */
export function GridView({ ctx, scene }: { ctx: Ctx; scene: Scene }) {
  const { heap, step } = ctx;
  const outer = scene.obj as SeqObj;
  const rows = outer.items.map((r) => deref(r, heap) as SeqObj | null);
  const rowOids = outer.items.map((r) => (r.t === "ref" ? r.r : ""));
  const cols = Math.max(0, ...rows.map((r) => r?.items.length ?? 0));

  const values = rows.flatMap((r) => (r?.items ?? []).map((x) => num(x))).filter((x): x is number => x !== null);
  const vmin = Math.min(0, ...values);
  const vmax = Math.max(1, ...values);

  const key = (r: number, c: number) => `${r},${c}`;
  const cmp = new Set<string>();
  const read = new Set<string>();
  const readRows = new Set<number>();
  let ghost: { r: number; c: number | null } | null = null;
  for (const a of step.acc ?? []) {
    if (!scene.names.includes(a.var)) continue;
    const r = num(a.idx[0]);
    const c = a.idx.length > 1 ? num(a.idx[1]) : null;
    if (r === null) continue;
    const rr = r < 0 ? r + rows.length : r;
    if (a.ok === false) ghost = { r, c };
    if (c === null) readRows.add(rr);
    else {
      const cc = c < 0 ? c + cols : c;
      (a.cmp ? cmp : read).add(key(rr, cc));
    }
  }
  const ev = ctx.error?.viz;
  if (ctx.atError && ev?.kind === "oob" && scene.names.includes(ev.var ?? "")) {
    ghost = (ev.depth ?? 0) === 0 ? { r: ev.idx ?? rows.length, c: null } : { r: ev.path?.[0] ?? 0, c: ev.idx ?? cols };
  }
  const written = new Set<string>();
  for (const o of step.ops) {
    const r = rowOids.indexOf(o.oid ?? "-");
    if (r >= 0 && o.k === "set") written.add(key(r, o.i!));
  }

  const ghostRow = ghost && ghost.c === null && ghost.r >= rows.length ? ghost.r : null;
  const ghostCol = ghost && ghost.c !== null && ghost.c >= cols ? ghost.c : null;
  const totalCols = ghostCol !== null ? ghostCol + 1 : cols;

  const heat = (v: number | null) => {
    if (v === null) return "#1b2540";
    const t = (v - vmin) / (vmax - vmin || 1);
    return `rgba(99, 102, 241, ${0.08 + t * 0.62})`;
  };

  const cell = Math.max(26, Math.min(48, 560 / Math.max(1, totalCols)));
  return (
    <div className="grid-wrap">
      <div className="grid" style={{ gridTemplateColumns: `28px repeat(${totalCols}, ${cell}px)` }}>
        <div />
        {Array.from({ length: totalCols }, (_, c) => (
          <div key={`h${c}`} className="grid-head" style={{ color: c >= cols ? C.bad : undefined }}>{c}</div>
        ))}
        {rows.map((row, r) => (
          <Fragment key={r}>
            <div className="grid-head" style={{ color: readRows.has(r) ? C.read : undefined }}>{r}</div>
            {Array.from({ length: totalCols }, (_, c) => {
              const it = row?.items[c];
              const k = key(r, c);
              const isGhost = ghost && ghost.c !== null && ghost.r === r && ghost.c === c;
              if (!it) {
                return isGhost ? <Ghost key={c} size={cell} /> : <div key={c} />;
              }
              const border = cmp.has(k) ? C.cmp : written.has(k) ? C.write : read.has(k) ? C.read : "transparent";
              return (
                <motion.div
                  key={written.has(k) ? `${c}@${ctx.i}` : c}
                  className="grid-cell"
                  style={{ width: cell, height: cell, background: heat(num(it)), borderColor: border,
                    boxShadow: border !== "transparent" ? `0 0 10px ${border}` : undefined }}
                  initial={written.has(k) ? { scale: 1.35 } : false}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 18 }}
                >
                  {label(it, heap)}
                </motion.div>
              );
            })}
          </Fragment>
        ))}
        {ghostRow !== null && (
          <>
            <div className="grid-head" style={{ color: C.bad }}>{ghostRow}</div>
            {Array.from({ length: totalCols }, (_, c) => <Ghost key={c} size={cell} />)}
          </>
        )}
      </div>
    </div>
  );
}

function Ghost({ size }: { size: number }) {
  return (
    <motion.div
      className="grid-cell ghost"
      style={{ width: size, height: size }}
      animate={{ opacity: [0.35, 1, 0.35] }}
      transition={{ repeat: Infinity, duration: 1.4 }}
    >
      ?
    </motion.div>
  );
}
