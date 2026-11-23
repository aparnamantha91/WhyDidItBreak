import { useEffect, useRef, useState } from "react";
import { useStore } from "../store";
import { Narration } from "./Inspector";

type Tab = "steps" | "output";

/** Panel under the editor: the step narration, and what print() has written so far. */
export function Console() {
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  const [tab, setTab] = useState<Tab>("steps");
  const upto = res?.steps.length ? res.steps[i].out : res?.stdout.length ?? 0;
  const prev = res && i > 0 && res.steps.length ? res.steps[i - 1].out : 0;
  const lines = res ? res.stdout.slice(0, upto).split("\n").filter(Boolean).length : 0;
  // the line just run printed something, and you're not looking at it
  const fresh = tab !== "output" && upto > prev;

  return (
    <div className="console">
      <div className="tabs console-tabs">
        <button className={tab === "steps" ? "on" : ""} onClick={() => setTab("steps")}>
          What just happened
        </button>
        <button
          className={tab === "output" ? "on" : ""}
          onClick={() => setTab("output")}
          title="Everything your code has print()-ed up to the current step"
        >
          Output
          {lines > 0 && <span className={`tab-badge ${fresh ? "new" : "count"}`}>{fresh ? "new" : lines}</span>}
        </button>
      </div>
      {tab === "steps" ? <Narration /> : <Output />}
    </div>
  );
}

function Output() {
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
    <>
      <div className="muted small console-hint">
        What your <code>print()</code> calls have written by this step. Dimmed text is printed later.
      </div>
      <pre ref={ref} className="console-body">
        {shown}
        {future && <span className="future">{future}</span>}
        {res && !res.stdout && <span className="muted">(nothing printed — add a print() to see values here)</span>}
        {!res && <span className="muted">(run your code first)</span>}
      </pre>
    </>
  );
}
