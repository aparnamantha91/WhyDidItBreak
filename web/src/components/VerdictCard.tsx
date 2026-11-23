import { useStore } from "../store";
import { Culprits, md } from "./ErrorCard";

/** Problem mode: how the traced test case went (shown above the error card and the structures). */
export function VerdictCard() {
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  const setStep = useStore((s) => s.setStep);
  const testIndex = useStore((s) => s.testIndex);
  const setHoverLine = useStore((s) => s.setHoverLine);
  const v = res?.verdict;
  if (!res || !v) return null;
  const name = testIndex < 0 ? "your input" : `test ${testIndex + 1}`;
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
    const why = v.why;
    return (
      <div className="verdict warn">
        <div className="v-title">❌ Wrong answer on {name}</div>
        <div className="v-grid">
          <span className="muted">input</span>
          <code>{v.input}</code>
          <span className="muted">expected</span>
          <Answer text={v.expected ?? ""} mark={why?.index} good />
          <span className="muted">returned</span>
          <Answer text={v.got ?? ""} mark={why?.index} />
        </div>
        {why ? (
          <div className="why">
            <div className="why-head">🔎 Where it went wrong</div>
            <div className="why-summary">{md(why.summary)}</div>
            {why.detail.length > 0 && (
              <ol className="why-steps">
                {why.detail.map((d, k) => (
                  <li key={k}>{md(d)}</li>
                ))}
              </ol>
            )}
            {why.culprits.length > 0 && <Culprits culprits={why.culprits} title="Values used on that line" />}
            {why.hint && (
              <div className="ec-hint">
                <span>💡</span>
                <span>{md(why.hint)}</span>
              </div>
            )}
            <div className="why-jumps">
              {why.jumps.map((j, k) => (
                <button key={k} className={`jump ${i === j.step ? "here" : ""}`} onClick={() => setStep(j.step)}
                  onMouseEnter={() => j.line && setHoverLine(j.line)} onMouseLeave={() => setHoverLine(null)}>
                  ⏪ {j.label}
                </button>
              ))}
              {ret !== undefined && (
                <button className={`jump ${i === ret ? "here" : ""}`} onClick={() => setStep(ret)}>
                  ⏩ the return
                </button>
              )}
            </div>
          </div>
        ) : (
          <>
            {v.diff && <div className="v-diff">{md(v.diff)}</div>}
            {ret !== undefined && i !== ret && (
              <button className="link" onClick={() => setStep(ret)}>
                ⏩ jump to the step where it returned
              </button>
            )}
          </>
        )}
        {v.note && <div className="muted small">{v.note}</div>}
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

/** A list answer with the first wrong position highlighted. */
function Answer({ text, mark, good }: { text: string; mark?: number; good?: boolean }) {
  const parts = mark === undefined ? null : splitTop(text);
  if (!parts || mark === undefined) return <code className={good ? "v-exp" : "badtext"}>{text}</code>;
  return (
    <code className={good ? "v-exp" : "v-got"}>
      [
      {parts.map((p, k) => (
        <span key={k}>
          {k > 0 && ", "}
          <span className={k === mark ? (good ? "mark-good" : "mark-bad") : undefined}>{p}</span>
        </span>
      ))}
      {!good && mark >= parts.length && <span className="mark-bad missing"> ␣ </span>}
      ]
    </code>
  );
}

/** "[1, [2, 3], 'a, b']" -> ["1", "[2, 3]", "'a, b'"] (top-level items only). */
function splitTop(text: string): string[] | null {
  const t = text.trim();
  if (!t.startsWith("[") || !t.endsWith("]")) return null;
  const body = t.slice(1, -1);
  if (!body.trim()) return [];
  const out: string[] = [];
  let depth = 0;
  let quote: string | null = null;
  let cur = "";
  for (const ch of body) {
    if (quote) {
      cur += ch;
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === "'" || ch === '"') quote = ch;
    else if ("[({".includes(ch)) depth++;
    else if ("])}".includes(ch)) depth--;
    if (ch === "," && depth === 0) {
      out.push(cur.trim());
      cur = "";
    } else cur += ch;
  }
  out.push(cur.trim());
  return out;
}
