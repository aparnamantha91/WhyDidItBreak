import { AnimatePresence, motion } from "framer-motion";
import { useStore } from "../store";
import { snapshot } from "../trace";

export function Inspector() {
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  if (!res || !res.steps.length) {
    return (
      <div className="inspector">
        <div className="pane-title">What's happening</div>
        <div className="muted pad">Narration, counters and the call stack appear here once you run.</div>
      </div>
    );
  }
  const step = res.steps[i];
  const { frames } = snapshot(res, i);
  const prevLine = i > 0 ? res.steps[i - 1].line : null;
  const c = step.cnt;
  return (
    <div className="inspector">
      <div className="insp-cols">
        <div className="narration">
          <div className="pane-title">What just happened</div>
          <AnimatePresence mode="wait">
            <motion.div key={i} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
              {step.did.length ? (
                <ul className="did">
                  {prevLine && step.ev === "line" && res.steps[i - 1].ev === "line" && <li className="muted small">after line {prevLine}:</li>}
                  {step.did.map((d, k) => (
                    <li key={k} className={d.startsWith("💥") ? "badtext" : d.startsWith("Swapped") ? "swap" : ""}>
                      {d}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="muted small">{step.ev === "line" ? "(no change)" : ""}</div>
              )}
              {step.next && <div className={`next ${step.next.includes("outside") ? "badtext" : ""}`}>👀 {step.next}</div>}
              <div className="nowline">
                ▶ about to run <b>line {step.line}</b>
                {step.fn !== "global" && <> in <code>{step.fn}()</code></>}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
        <div className="side">
          <div className="pane-title">Cost so far</div>
          <div className="counters">
            <Counter label="lines run" v={c.steps} />
            <Counter label="comparisons" v={c.cmp} />
            <Counter label="swaps" v={c.swaps} />
            <Counter label="writes" v={c.writes} />
            <Counter label="calls" v={Math.max(0, c.calls - 1)} />
          </div>
          <div className="pane-title">Call stack</div>
          <div className="callstack">
            {[...frames].reverse().map((f, k) => (
              <div key={f.fid} className={`frame ${k === 0 ? "top" : ""}`}>
                <code>{f.fn === "global" ? "<module>" : `${f.fn}()`}</code>
                <span className="muted small">line {f.line}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Counter({ label, v }: { label: string; v: number }) {
  return (
    <div className="counter">
      <motion.span key={v} className="counter-v" initial={{ y: -6, opacity: 0.4 }} animate={{ y: 0, opacity: 1 }}>
        {v}
      </motion.span>
      <span className="counter-l">{label}</span>
    </div>
  );
}
