import { useStore } from "../store";

const SPEEDS: [string, number][] = [
  ["0.1×", 4500],
  ["0.25×", 1800],
  ["0.5×", 900],
  ["1×", 450],
  ["2×", 220],
  ["4×", 100],
  ["10×", 35],
];

export function Toolbar() {
  const s = useStore();
  const n = s.res?.steps.length ?? 0;
  const err = s.res?.error;
  return (
    <div className="toolbar">
      <button className="icon-btn" title="Problems" onClick={s.togglePanel}>
        ☰
      </button>
      <div className="brand">
        <span className="brand-mark">
          <i style={{ height: 8 }} />
          <i style={{ height: 14 }} />
          <i style={{ height: 18, background: "#f43f5e" }} />
          <i style={{ height: 11 }} />
        </span>
        <span>
          Why<b>Did</b>It<span className="brand-break">Break</span>
        </span>
      </div>
      <button className="run-btn" onClick={s.run} disabled={s.running} title="Run (Ctrl/⌘ + Enter)">
        {s.running ? <span className="spinner small" /> : "▶"} Run
      </button>
      {s.problem && (!s.viewing || s.viewing.kind === "solution" || s.viewing.kind === "replay") && (
        <select className="speed" value={s.testIndex} onChange={(e) => s.setTest(Number(e.target.value))} title="Which test Run traces">
          {Array.from({ length: s.submitRes && !s.submitRes.fatal ? s.problem.total : s.problem.cases.length }, (_, k) => (
            <option key={k} value={k}>
              test {k + 1}
            </option>
          ))}
          {s.testIndex >= (s.submitRes && !s.submitRes.fatal ? s.problem.total : s.problem.cases.length) && (
            <option value={s.testIndex}>test {s.testIndex + 1}</option>
          )}
          <option value={-1}>my input</option>
        </select>
      )}
      {s.problem && (
        <button className="submit-btn" onClick={s.submit} disabled={s.submitting || s.running || !!s.viewing} title="Check every test">
          {s.submitting ? <span className="spinner small" /> : "✔"} Submit
        </button>
      )}
      <div className="transport">
        <button onClick={() => s.setStep(0)} disabled={!n} title="First step (Home)">⏮</button>
        <button onClick={() => s.stepBy(-1)} disabled={!n} title="Back (←)">◀</button>
        <button className="play" onClick={s.togglePlay} disabled={!n} title="Play / pause (Space)">
          {s.playing ? "⏸" : "⏵"}
        </button>
        <button onClick={() => s.stepBy(1)} disabled={!n} title="Forward (→)">▶</button>
        <button onClick={() => s.setStep(n - 1)} disabled={!n} title="Last step (End)">⏭</button>
      </div>
      <span className="stepcount">{n ? `step ${s.step + 1} / ${n}` : "no trace yet"}</span>
      <select className="speed" value={s.speed} onChange={(e) => s.setSpeed(Number(e.target.value))} title="Playback speed">
        {SPEEDS.map(([l, ms]) => (
          <option key={ms} value={ms}>
            {l}
          </option>
        ))}
      </select>
      {err && err.step !== undefined && (
        <button className="crash-btn" onClick={() => s.setStep(err.step!)}>
          💥 jump to crash
        </button>
      )}
      {s.dirty && s.res && s.view === "studio" && <span className="stale">changed — run again</span>}
      <button className={`learn-btn ${s.view === "learnings" ? "on" : ""}`} onClick={() => s.setView(s.view === "learnings" ? "studio" : "learnings")} title="Your progress, mistakes and run history">
        📈 Learnings
      </button>
    </div>
  );
}
