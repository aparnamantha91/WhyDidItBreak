import { AnimatePresence, motion } from "framer-motion";
import type { Scene } from "../detect";
import type { SeqObj } from "../types";
import { label } from "../trace";
import { C, type Ctx, opsFor } from "./common";

/** Number of items removed from the front of `oid` before step i (keeps queue items' identity stable). */
function frontShift(ctx: Ctx, oid: string | undefined): number {
  if (!oid) return 0;
  let n = 0;
  for (let k = 0; k <= ctx.i; k++) {
    for (const o of ctx.res.steps[k].ops) {
      if (o.oid !== oid) continue;
      if (o.k === "popleft" || (o.k === "remove" && o.i === 0)) n++;
      else if (o.k === "insert" && o.i === 0) n--;
    }
  }
  return n;
}

export function StackQueueView({ ctx, scene }: { ctx: Ctx; scene: Scene }) {
  const obj = scene.obj as SeqObj;
  const items = obj.items;
  const isStack = scene.kind === "stack";
  const ops = opsFor(ctx.step, scene.oid);
  const popped = ops.find((o) => o.k === "pop" || o.k === "popleft");
  const pushed = ops.find((o) => o.k === "append" || o.k === "insert");
  const ev = ctx.error?.viz;
  const empty = ctx.atError && ev?.kind === "empty" && scene.names.includes(ev.var ?? "");
  const shift = isStack ? 0 : frontShift(ctx, scene.oid);

  if (isStack) {
    return (
      <div className="stack-wrap">
        <div className="stack">
          <AnimatePresence initial={false}>
            {[...items].reverse().map((it, ri) => {
              const i = items.length - 1 - ri;
              const top = ri === 0;
              return (
                <motion.div
                  key={`${i}:${label(it, ctx.heap)}`}
                  className="stack-item"
                  layout
                  initial={{ y: -40, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: -40, x: 40, opacity: 0, rotate: 8 }}
                  transition={{ type: "spring", stiffness: 380, damping: 26 }}
                  style={top ? { borderColor: pushed ? C.ok : C.read, boxShadow: `0 0 12px ${pushed ? C.ok : C.read}66` } : undefined}
                >
                  <span className="si-idx">{i}</span>
                  {label(it, ctx.heap)}
                  {top && <span className="si-tag">top</span>}
                </motion.div>
              );
            })}
          </AnimatePresence>
          {items.length === 0 && (
            <motion.div
              className={`stack-empty ${empty ? "bad" : ""}`}
              animate={empty ? { opacity: [0.4, 1, 0.4] } : {}}
              transition={{ repeat: Infinity, duration: 1.3 }}
            >
              {empty ? "empty — can't pop!" : "empty"}
            </motion.div>
          )}
        </div>
        <div className="stack-base" />
        {popped && <div className="popped">popped <b>{popped.v}</b></div>}
      </div>
    );
  }

  return (
    <div className="queue-wrap">
      <div className="queue-labels">
        <span>front ←</span>
        <span>← back</span>
      </div>
      <div className="queue">
        <AnimatePresence initial={false} mode="popLayout">
          {items.map((it, i) => (
            <motion.div
              key={i + shift}
              className="queue-item"
              layout
              initial={{ x: 40, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -50, opacity: 0, scale: 0.8 }}
              transition={{ type: "spring", stiffness: 340, damping: 28 }}
              style={
                i === 0
                  ? { borderColor: C.read }
                  : i === items.length - 1 && pushed
                    ? { borderColor: C.ok, boxShadow: `0 0 10px ${C.ok}66` }
                    : undefined
              }
            >
              {label(it, ctx.heap)}
            </motion.div>
          ))}
        </AnimatePresence>
        {items.length === 0 && (
          <motion.div
            className={`stack-empty ${empty ? "bad" : ""}`}
            animate={empty ? { opacity: [0.4, 1, 0.4] } : {}}
            transition={{ repeat: Infinity, duration: 1.3 }}
          >
            {empty ? "empty — nothing to dequeue!" : "empty"}
          </motion.div>
        )}
      </div>
      {popped && <div className="popped">dequeued <b>{popped.v}</b></div>}
    </div>
  );
}
