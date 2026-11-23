import { useEffect, useState } from "react";
import { useStore, type Tab } from "../store";
import type { SubmitRow } from "../types";
import { md } from "./ErrorCard";

const LEVEL_ICON: Record<string, string> = { Beginner: "🌱", Intermediate: "🔥", Advanced: "🚀" };
const STATUS: Record<SubmitRow["status"], [string, string]> = {
  pass: ["✓", "Passed"],
  wrong: ["✗", "Wrong answer"],
  error: ["💥", "Crashed"],
  timeout: ["⏱", "Too slow"],
  skipped: ["–", "Not run"],
};

export function Problems() {
  const problem = useStore((s) => s.problem);
  const showList = useStore((s) => s.showList);
  return <div className="problems">{showList || !problem ? <ProblemList /> : <ProblemDetail />}</div>;
}

function ProblemList() {
  const { problems, levels, problem, progress, openProblem, openPlayground, setShowList } = useStore();
  const solved = problems.filter((p) => progress[p.id] === "solved").length;
  return (
    <>
      <div className="pl-head">
        <span className="pl-title">Problems</span>
        {problems.length > 0 && (
          <span className="muted small">
            {solved} / {problems.length} solved
          </span>
        )}
        {problem && (
          <button className="link pl-back" onClick={() => setShowList(false)}>
            back to {problem.title} →
          </button>
        )}
      </div>
      {levels.map((lvl) => (
        <div key={lvl} className="level">
          <div className="level-title">
            {LEVEL_ICON[lvl]} {lvl}
          </div>
          {problems
            .filter((p) => p.level === lvl)
            .map((p) => {
              const st = progress[p.id];
              return (
                <button key={p.id} className={`p-item ${problem?.id === p.id ? "active" : ""}`} onClick={() => openProblem(p.id)}>
                  <span className={`p-mark ${st ?? ""}`} title={st === "solved" ? "Solved" : st === "tried" ? "Attempted" : "Not started"}>
                    {st === "solved" ? "✓" : st === "tried" ? "●" : "○"}
                  </span>
                  <span className="p-name">{p.title}</span>
                  <span className="p-topic">{p.topic.replace(/-/g, " ")}</span>
                </button>
              );
            })}
        </div>
      ))}
      {!problems.length && <div className="muted pad small">Problems load from the Python server…</div>}
      <div className="level">
        <div className="level-title">🧪 Free practice</div>
        <button
          className={`p-item ${!problem ? "active" : ""}`}
          onClick={() => {
            openPlayground();
            setShowList(true);
          }}
        >
          <span className="p-mark">▷</span>
          <span className="p-name">Playground</span>
          <span className="p-topic">run any code</span>
        </button>
      </div>
    </>
  );
}

const TABS: [Tab, string][] = [
  ["desc", "Description"],
  ["tests", "Tests"],
  ["sample", "Sample"],
  ["solution", "Solution"],
];

function ProblemDetail() {
  const problem = useStore((s) => s.problem)!;
  const tab = useStore((s) => s.tab);
  const setTab = useStore((s) => s.setTab);
  const setShowList = useStore((s) => s.setShowList);
  const resetCode = useStore((s) => s.resetCode);
  const status = useStore((s) => s.progress[problem.id]);
  const submitRes = useStore((s) => s.submitRes);
  return (
    <>
      <div className="pd-top">
        <button className="link" onClick={() => setShowList(true)}>
          ← All problems
        </button>
        <button
          className="link dim"
          title="Throw away your code for this problem and start from the starter again"
          onClick={() => window.confirm("Replace your code for this problem with the starter code?") && resetCode()}
        >
          ↺ reset my code
        </button>
      </div>
      <div className="pd-title">
        {problem.title}
        {status === "solved" && <span className="pd-solved">✓ Solved</span>}
      </div>
      <div className="pd-meta">
        {LEVEL_ICON[problem.level]} {problem.level} · {problem.topic.replace(/-/g, " ")}
      </div>
      <div className="tabs">
        {TABS.map(([t, label]) => (
          <button key={t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
            {label}
            {t === "tests" && submitRes && !submitRes.fatal && (
              <span className={`tab-badge ${submitRes.passed === submitRes.total ? "ok" : "bad"}`}>
                {submitRes.passed}/{submitRes.total}
              </span>
            )}
          </button>
        ))}
      </div>
      {tab === "desc" && <Description />}
      {tab === "tests" && <Tests />}
      {tab === "sample" && <Sample />}
      {tab === "solution" && <Solution key={problem.id} />}
    </>
  );
}

function Description() {
  const problem = useStore((s) => s.problem)!;
  const runTest = useStore((s) => s.runTest);
  const running = useStore((s) => s.running);
  const [hints, setHints] = useState(0);
  useEffect(() => setHints(0), [problem.id]);
  return (
    <div className="pd-body">
      <p className="pd-statement">{md(problem.statement)}</p>
      <p className="muted small">
        Write the function <code>{problem.fn}({problem.params.join(", ")})</code> in the editor. <b>Run</b> traces it on one
        example; <b>Submit</b> checks all {problem.total} tests and takes you to the first one that breaks.
      </p>
      {problem.cases.map((c, k) => (
        <div key={c.index} className="example">
          <div className="ex-head">
            <span>Example {k + 1}</span>
            <button className="link" disabled={running} onClick={() => runTest(c.index)}>
              ▶ run this
            </button>
          </div>
          <div className="ex-row">
            <span className="muted">Input</span> <code>{c.input}</code>
          </div>
          <div className="ex-row">
            <span className="muted">Output</span> <code>{c.expected}</code>
          </div>
          {c.explain && <div className="ex-note">{md(c.explain)}</div>}
        </div>
      ))}
      {problem.constraints.length > 0 && (
        <>
          <div className="pd-sub">Constraints</div>
          <ul className="pd-list">
            {problem.constraints.map((c, k) => (
              <li key={k}>{md(c)}</li>
            ))}
          </ul>
        </>
      )}
      {problem.hints.length > 0 && (
        <>
          <div className="pd-sub">Hints</div>
          {problem.hints.slice(0, hints).map((h, k) => (
            <div key={k} className="hint">
              <span>💡</span>
              <span>{md(h)}</span>
            </div>
          ))}
          {hints < problem.hints.length && (
            <button className="ghost-btn" onClick={() => setHints(hints + 1)}>
              Show hint {hints + 1} of {problem.hints.length}
            </button>
          )}
        </>
      )}
    </div>
  );
}

function Tests() {
  const { problem, submitRes, testIndex, custom, running, submitting, dirty } = useStore();
  const { runTest, setCustom, setTest, submit } = useStore();
  if (!problem) return null;
  const rows: SubmitRow[] | null = submitRes && !submitRes.fatal ? submitRes.results : null;
  return (
    <div className="pd-body">
      {submitRes?.fatal && (
        <div className="verdict bad">
          <b>{submitRes.fatal.title ?? submitRes.fatal.type}</b>
          <div>{md(submitRes.fatal.why ?? submitRes.fatal.msg)}</div>
          {submitRes.fatal.hint && <div className="muted">{md(submitRes.fatal.hint)}</div>}
        </div>
      )}
      {rows && (
        <div className={`sub-summary ${submitRes!.passed === submitRes!.total ? "ok" : "bad"}`}>
          {submitRes!.passed === submitRes!.total
            ? `🎉 All ${submitRes!.total} tests passed.`
            : `${submitRes!.passed} of ${submitRes!.total} tests passed. Click a failed test to watch it break.`}
          {dirty && <div className="muted small">Results are from your last submit.</div>}
        </div>
      )}
      {(rows ?? problem.cases.map((c) => ({ ...c, status: null }))).map((r) => {
        const st = r.status as SubmitRow["status"] | null;
        const row = r as SubmitRow;
        return (
          <button
            key={r.index}
            className={`test-row ${st ?? ""} ${testIndex === r.index ? "active" : ""}`}
            disabled={running || st === "skipped"}
            onClick={() => runTest(r.index)}
            title="Trace this test"
          >
            <div className="tr-head">
              <span className="tr-icon">{st ? STATUS[st][0] : "▶"}</span>
              <span>Test {r.index + 1}</span>
              {st && <span className="tr-status">{STATUS[st][1]}</span>}
            </div>
            <code className="tr-io">{r.input}</code>
            {r.expected && (
              <div className="tr-line">
                <span className="muted">expected</span> <code>{r.expected}</code>
              </div>
            )}
            {st === "wrong" && (
              <div className="tr-line">
                <span className="muted">got</span> <code className="badtext">{row.got}</code>
              </div>
            )}
            {st === "error" && row.error && (
              <div className="tr-line badtext">
                {row.error.type}: {row.error.msg}
                {row.error.line ? ` (line ${row.error.line})` : ""}
              </div>
            )}
          </button>
        );
      })}
      {!rows && problem.total > problem.cases.length && (
        <p className="muted small">
          +{problem.total - problem.cases.length} more tests run when you submit.
        </p>
      )}
      <div className="pd-sub">Your own input</div>
      <p className="muted small">One argument per line, as Python values: {problem.params.map((p) => <code key={p}>{p}</code>)}</p>
      <textarea
        className={`custom ${testIndex < 0 ? "active" : ""}`}
        rows={Math.max(2, problem.params.length)}
        spellCheck={false}
        placeholder={problem.cases[0]?.input.split(", ").length === problem.params.length ? problem.cases[0].input.split(/, (?=\w+ = )/).map((x) => x.replace(/^\w+ = /, "")).join("\n") : ""}
        value={custom}
        onChange={(e) => setCustom(e.target.value)}
        onFocus={() => setTest(-1)}
      />
      <div className="row-btns">
        <button className="ghost-btn" disabled={running || !custom.trim()} onClick={() => runTest(-1)}>
          ▶ Run on my input
        </button>
        <button className="ghost-btn strong" disabled={submitting} onClick={submit}>
          ✔ Submit all tests
        </button>
      </div>
    </div>
  );
}

function Sample() {
  const problem = useStore((s) => s.problem)!;
  const viewing = useStore((s) => s.viewing);
  const watch = useStore((s) => s.watch);
  const running = useStore((s) => s.running);
  const [buggy, setBuggy] = useState(false);
  const lesson = problem.lesson;
  if (!lesson) return <div className="pd-body muted">No sample for this topic.</div>;
  return (
    <div className="pd-body">
      <div className="pd-sub first">{lesson.title}</div>
      <p className="pd-statement">{md(lesson.concept)}</p>
      <p className="muted small">
        A worked example of the technique this problem practises. Watching it leaves your own code untouched.
      </p>
      <div className="seg">
        <button className={!buggy ? "on" : ""} onClick={() => setBuggy(false)}>
          ✓ Working
        </button>
        <button className={buggy ? "on bug" : ""} onClick={() => setBuggy(true)}>
          🐞 With a typical bug
        </button>
      </div>
      <pre className="ref-code">{buggy ? lesson.buggy : lesson.code}</pre>
      <button className="ghost-btn strong" disabled={running} onClick={() => watch(buggy ? "buggy" : "sample")}>
        ▶ {viewing?.kind === (buggy ? "buggy" : "sample") ? "Run it again" : buggy ? "Watch it break" : "Watch it run"}
      </button>
    </div>
  );
}

function Solution() {
  const problem = useStore((s) => s.problem)!;
  const watch = useStore((s) => s.watch);
  const running = useStore((s) => s.running);
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <div className="pd-body">
        <div className="reveal">
          <div className="reveal-title">Reference solution</div>
          <p className="muted">
            Stuck? Try the hints and the sample code first. You learn most from the bug you find yourself.
          </p>
          <button className="ghost-btn" onClick={() => setOpen(true)}>
            Reveal the solution
          </button>
        </div>
      </div>
    );
  }
  return (
    <div className="pd-body">
      <pre className="ref-code">{problem.solution}</pre>
      <button className="ghost-btn strong" disabled={running} onClick={() => watch("solution")}>
        ▶ Watch it run on the selected test
      </button>
      <p className="muted small">Watching it leaves your own code untouched.</p>
    </div>
  );
}
