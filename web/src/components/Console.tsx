import { useEffect, useRef } from "react";
import { useStore } from "../store";

export function Console() {
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  const ref = useRef<HTMLPreElement>(null);
  const upto = res?.steps.length ? res.steps[i].out : res?.stdout.length ?? 0;
  const shown = res ? res.stdout.slice(0, upto) : "";
  const future = res ? res.stdout.slice(upto) : "";

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [upto]);

  return (
    <div className="console">
      <div className="pane-title">
        Output
        {res && <span className="muted small"> · printed so far at this step</span>}
      </div>
      <pre ref={ref} className="console-body">
        {shown}
        {future && <span className="future">{future}</span>}
        {res && !res.stdout && <span className="muted">(nothing printed)</span>}
      </pre>
    </div>
  );
}

/** Lesson output check: compares with the reference solution and points at the first wrong print. */
export function OutputCheck() {
  const res = useStore((s) => s.res);
  const lesson = useStore((s) => s.lesson);
  const variant = useStore((s) => s.variant);
  const setStep = useStore((s) => s.setStep);
  const i = useStore((s) => s.step);
  if (!res || !lesson || lesson.expected == null || res.error || !variant) return null;
  const got = res.stdout;
  const exp = lesson.expected;
  if (got === exp) {
    if (i < res.steps.length - 1) return null; // celebrate once the program has finished
    return <div className="check ok">✅ Output matches the expected answer for “{lesson.title}”.</div>;
  }
  let d = 0;
  while (d < got.length && d < exp.length && got[d] === exp[d]) d++;
  const stepIdx = res.steps.findIndex((s) => s.out > d);
  const lineStart = got.lastIndexOf("\n", d - 1) + 1;
  const gotLine = got.slice(lineStart).split("\n")[0];
  const expLine = exp.slice(exp.lastIndexOf("\n", d - 1) + 1).split("\n")[0];
  return (
    <div className="check bad">
      <div>
        ❌ <b>No crash, but the answer is wrong.</b> This is a logic bug — the program ran fine but computed the wrong thing.
      </div>
      <div className="diff">
        <div>
          <span className="muted">expected</span> <code>{expLine || "(nothing)"}</code>
        </div>
        <div>
          <span className="muted">got</span> <code className="badtext">{gotLine || "(nothing)"}</code>
        </div>
      </div>
      {stepIdx >= 0 && (
        <button className="link" onClick={() => setStep(Math.max(0, stepIdx - 1))}>
          ⏪ jump to the step that printed the first wrong output
        </button>
      )}
    </div>
  );
}
