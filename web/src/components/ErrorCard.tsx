import { motion } from "framer-motion";
import type { Culprit, ErrorInfo } from "../types";
import { useStore } from "../store";

export function ErrorCard({ error, atError, total }: { error: ErrorInfo; atError: boolean; total: number }) {
  const setStep = useStore((s) => s.setStep);
  const setHoverLine = useStore((s) => s.setHoverLine);
  const hasStep = error.step !== undefined && total > 0;

  if (!atError && hasStep) {
    return (
      <button className="crash-banner" onClick={() => setStep(error.step!)}>
        <span className="pulse-dot" /> This run breaks at step {error.step! + 1} (line {error.line}) —{" "}
        <b>{error.title}</b>. Jump to the crash →
      </button>
    );
  }

  return (
    <motion.div className="error-card" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
      <div className="ec-head">
        <span className="ec-icon">💥</span>
        <div>
          <div className="ec-title">{error.title ?? error.type}</div>
          <div className="ec-type">
            {error.type}
            {error.msg ? `: ${error.msg}` : ""}
          </div>
        </div>
        {error.line ? <span className="ec-line">line {error.line}</span> : null}
      </div>
      {error.code && <pre className="ec-code">{error.code}</pre>}
      {error.why && <p className="ec-why">{md(error.why)}</p>}

      {error.viz?.kind === "recursion" && error.viz.calls && (
        <div className="ec-calls">
          <span className="muted small">calls to {error.viz.fn}():</span>
          <div className="ec-callrow">
            {error.viz.calls.map((c, k) => (
              <span key={k} className={`ec-call ${c === "…" ? "gap" : ""}`}>
                {c === "…" ? "…" : `${error.viz!.fn}(${c})`}
              </span>
            ))}
          </div>
        </div>
      )}

      {error.culprits.length > 0 && <Culprits culprits={error.culprits} />}
      {error.hint && (
        <div className="ec-hint">
          <span>💡</span>
          <span>{md(error.hint)}</span>
        </div>
      )}
    </motion.div>
  );
}

/** Variables involved, each with its value history; click a value to jump to the step that set it. */
export function Culprits({ culprits, title = "Values involved" }: { culprits: Culprit[]; title?: string }) {
  const setStep = useStore((s) => s.setStep);
  const setHoverLine = useStore((s) => s.setHoverLine);
  return (
    <div className="ec-culprits">
          <div className="ec-sub">{title}</div>
          {culprits.map((c) => (
            <div key={c.name} className="culprit">
              <div className="culprit-head">
                <code className="culprit-name">{c.name}</code>
                <span className="culprit-eq">=</span>
                <code className="culprit-val">{c.value}</code>
                <span className="culprit-type">{c.type}</span>
                {c.note && <span className="culprit-note">{md(c.note)}</span>}
              </div>
              {c.history.length > 0 && (
                <div className="history">
                  {c.history.map((h, k) => (
                    <button
                      key={k}
                      className={`hist ${k === c.history.length - 1 ? "last" : ""}`}
                      title={`set on line ${h.line} — click to jump to step ${h.step + 1}`}
                      onClick={() => setStep(h.step)}
                      onMouseEnter={() => setHoverLine(h.line)}
                      onMouseLeave={() => setHoverLine(null)}
                    >
                      {h.v}
                      <span className="hist-line">L{h.line}</span>
                    </button>
                  ))}
                </div>
              )}
              {c.changed_step !== undefined && (
                <button className="link" onClick={() => setStep(c.changed_step!)}
                  onMouseEnter={() => setHoverLine(c.changed_line ?? null)} onMouseLeave={() => setHoverLine(null)}>
                  ⏪ see where {c.name} became {c.value} (line {c.changed_line})
                </button>
              )}
            </div>
          ))}
        </div>
  );
}

/** Tiny markdown: `code` spans, **strong** and *emphasis*. */
export function md(text: string) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((p, k) =>
    p.startsWith("`") ? (
      <code key={k}>{p.slice(1, -1)}</code>
    ) : p.startsWith("**") ? (
      <b key={k}>{p.slice(2, -2)}</b>
    ) : p.startsWith("*") ? (
      <em key={k}>{p.slice(1, -1)}</em>
    ) : (
      p
    ),
  );
}
