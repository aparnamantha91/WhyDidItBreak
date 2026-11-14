import { AnimatePresence, motion } from "framer-motion";
import type { Scene } from "../detect";
import type { DictObj, SeqObj } from "../types";
import { label, show } from "../trace";
import { C, type Ctx, opsFor } from "./common";

/** dict as key → value rows; set as a cloud of chips. */
export function HashView({ ctx, scene }: { ctx: Ctx; scene: Scene }) {
  const { heap, step } = ctx;
  const ops = opsFor(step, scene.oid);
  const acc = (step.acc ?? []).filter((a) => scene.names.includes(a.var) && a.idx.length >= 1);
  const accKeys = new Map<string, { cmp: boolean; ok?: boolean }>();
  for (const a of acc) accKeys.set(show(a.idx[0], heap), { cmp: a.cmp, ok: a.ok });
  const ev = ctx.error?.viz;
  const missing = ctx.atError && ev?.kind === "missing_key" && scene.names.includes(ev.var ?? "") ? ev.key : null;

  if (scene.obj!.t === "set") {
    const obj = scene.obj as SeqObj;
    const added = new Set(ops.filter((o) => o.k === "add").map((o) => o.v));
    return (
      <div className="set-cloud">
        {obj.items.length === 0 && <span className="muted">set() — empty</span>}
        <AnimatePresence initial={false}>
          {obj.items.map((it) => {
            const s = show(it, heap);
            return (
              <motion.span
                layout
                key={s}
                className="chip"
                initial={{ scale: 0.3, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.3, opacity: 0 }}
                style={added.has(s) ? { borderColor: C.ok, boxShadow: `0 0 10px ${C.ok}` } : undefined}
              >
                {label(it, heap)}
              </motion.span>
            );
          })}
        </AnimatePresence>
      </div>
    );
  }

  const obj = scene.obj as DictObj;
  const changed = new Map(ops.filter((o) => o.k === "dset").map((o) => [o.key!, o]));
  return (
    <div className="hash">
      {obj.entries.length === 0 && !missing && <div className="muted">{"{ }"} empty</div>}
      <AnimatePresence initial={false}>
        {obj.entries.map(([k, v]) => {
          const ks = show(k, heap);
          const ch = changed.get(ks);
          const a = accKeys.get(ks);
          const col = a?.cmp ? C.cmp : ch ? (ch.new ? C.ok : C.write) : a ? C.read : undefined;
          return (
            <motion.div
              layout
              key={ks}
              className="hash-row"
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 16 }}
              style={col ? { borderColor: col, boxShadow: `0 0 12px ${col}55` } : undefined}
            >
              <span className="hash-key">{label(k, heap)}</span>
              <span className="hash-arrow">→</span>
              <motion.span
                key={ch ? `${ks}@${ctx.i}` : ks}
                className="hash-val"
                initial={ch && !ch.new ? { scale: 1.25, color: C.write } : false}
                animate={{ scale: 1, color: C.text }}
              >
                {show(v, heap)}
              </motion.span>
              {ch && !ch.new && <span className="hash-old">was {ch.old}</span>}
            </motion.div>
          );
        })}
      </AnimatePresence>
      {missing && (
        <motion.div className="hash-row ghost" animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.4 }}>
          <span className="hash-key">{missing}</span>
          <span className="hash-arrow">→</span>
          <span className="hash-val">not found!</span>
        </motion.div>
      )}
      {obj.more ? <div className="muted">+{obj.more} more</div> : null}
    </div>
  );
}
