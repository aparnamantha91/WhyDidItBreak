import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useStore } from "../store";
import { show, snapshot } from "../trace";

/** Bottom-of-editor narration: a scrolling log of what each line did, plus the current step. */
export function Narration() {
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  const setStep = useStore((s) => s.setStep);
  const logRef = useRef<HTMLDivElement>(null);
  // keep the newest line of the log in view while stepping or playing
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [i, res]);
  if (!res || !res.steps.length) {
    return (
      <div className="muted pad">
        Run your code and each line's effect is narrated here, step by step.
      </div>
    );
  }
  const step = res.steps[i];
  const { heap } = snapshot(res, i);
  // the last few things that happened, so a line doesn't vanish the moment the next step starts
  const log: { k: number; s: typeof step }[] = [];
  for (let k = Math.max(0, i - 40); k < i; k++)
    if (res.steps[k].did.length) log.push({ k, s: res.steps[k] });
  return (
    <div className="narration">
      <div className="log" ref={logRef}>
        {log.map(({ k, s }) => (
          <button
            key={k}
            className="log-row"
            onClick={() => setStep(k)}
            title={`Jump back to step ${k + 1}`}
          >
            <span className="log-step">{k + 1}</span>
            <span className="log-text">{s.did.join(" · ")}</span>
          </button>
        ))}
      </div>
      <div className="now">
        {step.did.length ? (
          <ul className="did">
            {step.did.map((d, k) => (
              <li
                key={k}
                className={
                  d.startsWith("💥")
                    ? "badtext"
                    : d.startsWith("Swapped")
                      ? "swap"
                      : ""
                }
              >
                {d}
              </li>
            ))}
          </ul>
        ) : step.ev !== "return" ? (
          <div className="muted">
            {i > 0 ? "(nothing changed on the last line)" : "Ready to start."}
          </div>
        ) : null}
        {step.ev === "return" && step.ret && (
          <div className="ret">
            ↩{" "}
            <code>{step.fn === "global" ? "the program" : `${step.fn}()`}</code>{" "}
            returns <b>{show(step.ret, heap)}</b>
          </div>
        )}
        {step.next && (
          <div
            className={`next ${step.next.includes("outside") ? "badtext" : ""}`}
          >
            👀 {step.next}
          </div>
        )}
        <div className="nowline">
          <span className="log-step">{i + 1}</span> ▶ about to run{" "}
          <b>line {step.line}</b>
          {step.fn !== "global" && (
            <>
              {" "}
              in <code>{step.fn}()</code>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/** Right-hand stats: operation counters and the live call stack. */
export function Inspector() {
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  if (!res || !res.steps.length) {
    return (
      <div className="inspector">
        <div className="pane-title">Cost so far</div>
        <div className="muted pad">
          Counters and the call stack appear here once you run.
        </div>
      </div>
    );
  }
  const { frames } = snapshot(res, i);
  const c = res.steps[i].cnt;
  return (
    <div className="inspector">
      <div className="side">
        <div className="pane-title">Cost so far</div>
        <div className="counters">
          <Counter label="lines run" v={c.steps} />
          <Counter label="comparisons" v={c.cmp} />
          <Counter label="swaps" v={c.swaps} />
          <Counter label="writes" v={c.writes} />
          <Counter label="calls" v={c.calls} />
        </div>
        <div className="pane-title">Call stack</div>
        <div className="callstack">
          {[...frames].reverse().map((f, k) => (
            <div key={f.fid} className={`frame ${k === 0 ? "top" : ""}`}>
              <code>{f.fn === "global" ? "<module>" : `${f.fn}()`}</code>
              {f.line > 0 && <span className="muted small">line {f.line}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Counter({ label, v }: { label: string; v: number }) {
  return (
    <div className="counter">
      <motion.span
        key={v}
        className="counter-v"
        initial={{ y: -6, opacity: 0.4 }}
        animate={{ y: 0, opacity: 1 }}
      >
        {v}
      </motion.span>
      <span className="counter-l">{label}</span>
    </div>
  );
}
