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
