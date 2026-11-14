import { useStore } from "../store";
import { md } from "./ErrorCard";

/** Problem mode: how the traced test case went (shown above the error card and the structures). */
export function VerdictCard() {
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  const setStep = useStore((s) => s.setStep);
  const testIndex = useStore((s) => s.testIndex);
  const viewing = useStore((s) => s.viewing);
  const v = res?.verdict;
  if (!res || !v) return null;
  const name = testIndex < 0 ? "your input" : `test ${testIndex + 1}`;
  const who = viewing ? "The reference solution" : "Your function";
  const long = res.truncated && (
    <div className="muted small">This run is long: the visualizer shows its first {res.steps.length} steps.</div>
  );

  if (v.status === "pass") {
    return (
      <div className="verdict ok">
        <div>
          ✅ <b>Passed {name}.</b> <code>{v.input}</code> → <code>{v.got}</code>
        </div>
        {long}
      </div>
    );
  }
  if (v.status === "wrong") {
    const ret = res.return_step;
    return (
      <div className="verdict warn">
        <div className="v-title">❌ Wrong answer on {name}</div>
        <div className="muted">{who} ran without crashing but returned the wrong value: a logic bug.</div>
        <div className="v-grid">
          <span className="muted">input</span>
          <code>{v.input}</code>
          <span className="muted">expected</span>
          <code className="v-exp">{v.expected}</code>
          <span className="muted">returned</span>
          <code className="badtext">{v.got}</code>
        </div>
        {v.diff && <div className="v-diff">{md(v.diff)}</div>}
        {v.note && <div className="muted small">{v.note}</div>}
        {ret !== undefined && (
          <div className="v-actions">
            {i !== ret ? (
              <button className="link" onClick={() => setStep(ret)}>
                ⏩ jump to the step where it returned
              </button>
            ) : (
              <span className="muted small">
                This is the return. Step backwards (←) and watch for the first value that isn't what you expected.
              </span>
            )}
          </div>
        )}
        {long}
      </div>
    );
  }
  return (
    <div className="verdict bad">
      <div>
        {v.status === "timeout" ? "⏱ " : "💥 "}
        <b>{v.status === "timeout" ? `Too slow on ${name}` : `Crashed on ${name}`}</b> <code>{v.input}</code>
      </div>
      {v.expected && (
        <div className="muted small">
          expected <code>{v.expected}</code>
        </div>
      )}
    </div>
  );
}
