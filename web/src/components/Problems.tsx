import { useEffect, useMemo, useState } from "react";
import { load, save, useStore, type Tab } from "../store";
import type { SubmitRow } from "../types";
import { md } from "./ErrorCard";
import { duration } from "../format";

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

const WINDOWS: [string, string][] = [
  ["all", "all time"],
  ["30d", "last 30 days"],
  ["3m", "last 3 months"],
  ["6m", "last 6 months"],
  ["older", "over 6 months ago"],
];
const PAGE = 60;

type Filters = { q: string; company: string; window: string; topic: string; status: string; source: string };
const NO_FILTERS: Filters = { q: "", company: "", window: "all", topic: "", status: "", source: "" };

function useFilters(): [Filters, (f: Partial<Filters>) => void] {
  const [f, setF] = useState<Filters>(() => {
    try {
      return { ...NO_FILTERS, ...JSON.parse(load("wdib.filters", "{}")) };
    } catch {
      return NO_FILTERS;
    }
  });
  const update = (patch: Partial<Filters>) =>
    setF((old) => {
      const next = { ...old, ...patch };
      save("wdib.filters", JSON.stringify(next));
      return next;
    });
  return [f, update];
}

function ProblemList() {
  const { problems, levels, companies, problem, progress, openProblem, openPlayground, setShowList } = useStore();
  const [f, setFilter] = useFilters();
  const [companyText, setCompanyText] = useState(f.company);
  const [freq, setFreq] = useState<Record<string, number> | null>(null);
  const [shown, setShown] = useState<Record<string, number>>({});

  // one company's frequency map for the chosen time window
  useEffect(() => {
    if (!f.company) return setFreq(null);
    let live = true;
    fetch(`/api/companies/${encodeURIComponent(f.company)}?window=${f.window}`)
      .then((r) => r.json())
      .then((j) => live && setFreq(j.frequency ?? {}))
      .catch(() => live && setFreq({}));
    return () => {
      live = false;
    };
  }, [f.company, f.window]);

  const topics = useMemo(
    () => [...new Set(problems.map((p) => p.topic).filter((t): t is string => !!t))].sort(),
    [problems],
  );
  const q = f.q.trim().toLowerCase();
  const visible = problems.filter((p) => {
    if (q && !p.title.toLowerCase().includes(q)) return false;
    if (f.topic && p.topic !== f.topic) return false;
    if (f.source && (f.source === "curriculum") !== p.builtin) return false;
    const st = progress[p.id]?.status;
    if (f.status === "solved" && st !== "solved") return false;
    if (f.status === "unsolved" && st === "solved") return false;
    if (f.company && freq && !(p.id in freq)) return false;
    return true;
  });
  if (f.company && freq) visible.sort((a, b) => (freq[b.id] ?? 0) - (freq[a.id] ?? 0));
  const solved = problems.filter((p) => progress[p.id]?.status === "solved").length;
  const filtering = JSON.stringify(f) !== JSON.stringify(NO_FILTERS);

  const pickCompany = (name: string) => {
    setCompanyText(name);
    const hit = companies.find((c) => c.toLowerCase() === name.trim().toLowerCase());
    if (hit) setFilter({ company: hit });
    else if (!name.trim()) setFilter({ company: "" });
  };

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
      {problems.length > 0 && (
        <div className="filters">
          <input
            className="f-search"
            placeholder="Search problems…"
            value={f.q}
            onChange={(e) => setFilter({ q: e.target.value })}
          />
          <div className="f-row">
            <input
              className={`f-company ${f.company ? "set" : ""}`}
              list="wdib-companies"
              placeholder={`Company (${companies.length})`}
              value={companyText}
              onChange={(e) => pickCompany(e.target.value)}
            />
            <datalist id="wdib-companies">
              {companies.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
            {f.company && (
              <select value={f.window} onChange={(e) => setFilter({ window: e.target.value })} title="When the company asked it">
                {WINDOWS.map(([k, label]) => (
                  <option key={k} value={k}>
                    {label}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="f-row">
            <select value={f.topic} onChange={(e) => setFilter({ topic: e.target.value })}>
              <option value="">Any topic</option>
              {topics.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/-/g, " ")}
                </option>
              ))}
            </select>
            <select value={f.status} onChange={(e) => setFilter({ status: e.target.value })}>
              <option value="">Any status</option>
              <option value="unsolved">Unsolved</option>
              <option value="solved">Solved</option>
            </select>
            <select value={f.source} onChange={(e) => setFilter({ source: e.target.value })}>
              <option value="">All sets</option>
              <option value="curriculum">Curriculum</option>
              <option value="bank">Company bank</option>
            </select>
          </div>
          {filtering && (
            <div className="f-summary muted small">
              {visible.length} match{visible.length === 1 ? "" : "es"}
              {f.company && freq && <> · sorted by how often {f.company} asks</>}
              <button
                className="link"
                onClick={() => {
                  setCompanyText("");
                  setFilter(NO_FILTERS);
                }}
              >
                clear
              </button>
            </div>
          )}
        </div>
      )}
      {levels.map((lvl) => {
        const rows = visible.filter((p) => p.level === lvl);
        if (!rows.length && filtering) return null;
        const limit = shown[lvl] ?? PAGE;
        const top = f.company && freq ? Math.max(1, ...rows.map((p) => freq[p.id] ?? 0)) : 0;
        return (
          <div key={lvl} className="level">
            <div className="level-title">
              {LEVEL_ICON[lvl]} {lvl} <span className="level-count">{rows.length}</span>
            </div>
            {rows.slice(0, limit).map((p) => {
              const st = progress[p.id]?.status;
              return (
                <button key={p.id} className={`p-item ${problem?.id === p.id ? "active" : ""}`} onClick={() => openProblem(p.id)}>
                  <span className={`p-mark ${st ?? ""}`} title={st === "solved" ? "Solved" : st === "tried" ? "Attempted" : "Not started"}>
                    {st === "solved" ? "✓" : st === "tried" ? "●" : "○"}
                  </span>
                  <span className="p-name">{p.title}</span>
                  {top ? (
                    <span className="p-freq" title={`Frequency ${freq![p.id] ?? 0}`}>
                      <span style={{ width: `${Math.round(((freq![p.id] ?? 0) / top) * 100)}%` }} />
                    </span>
                  ) : p.companies.length ? (
                    <span className="p-topic" title={p.companies.map((i) => companies[i]).join(", ")}>
                      {p.companies.length} co.
                    </span>
                  ) : (
                    <span className="p-topic">{p.topic?.replace(/-/g, " ")}</span>
                  )}
                </button>
              );
            })}
            {rows.length > limit && (
              <button className="link more" onClick={() => setShown({ ...shown, [lvl]: limit + 200 })}>
                show {Math.min(200, rows.length - limit)} more of {rows.length - limit}
              </button>
            )}
          </div>
        );
      })}
      {!problems.length && <div className="muted pad small">Problems load from the Python server…</div>}
      {filtering && !visible.length && <div className="muted pad small">No problems match these filters.</div>}
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
  const row = useStore((s) => s.progress[problem.id]);
  const pending = useStore((s) => s.pendingActive);
  const status = row?.status;
  const submitRes = useStore((s) => s.submitRes);
  return (
    <>
      <div className="pd-top">
        <button className="link" onClick={() => setShowList(true)}>
          ← All problems
        </button>
        <button className="link dim" title="Clear this problem's progress, time and run history" onClick={() => resetProblemPrompt(problem.id, problem.title)}>
          ⟲ reset progress
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
        {LEVEL_ICON[problem.level]} {problem.level}
        {problem.topic && <> · {problem.topic.replace(/-/g, " ")}</>}
      </div>
      {problem.companies?.length > 0 && <CompanyTags names={problem.companies} />}
      <div className="pd-stats" title="Active time counts only while you're working in this tab">
        ⏱ {duration((row?.active_seconds ?? 0) + pending)} active
        {row?.seconds_to_solve != null && <> · solved in {duration(row.seconds_to_solve)}</>}
        {row && (row.runs > 0 || row.submits > 0) && (
          <>
            {" "}· {row.runs} run{row.runs === 1 ? "" : "s"}, {row.submits} submit{row.submits === 1 ? "" : "s"}
          </>
        )}
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

function CompanyTags({ names }: { names: string[] }) {
  const [all, setAll] = useState(false);
  const shown = all ? names : names.slice(0, 6);
  return (
    <div className="co-tags" title="Companies that have asked this problem">
      {shown.map((c) => (
        <span key={c} className="co-tag">
          {c}
        </span>
      ))}
      {names.length > shown.length && (
        <button className="link small" onClick={() => setAll(true)}>
          +{names.length - shown.length} more
        </button>
      )}
    </div>
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
  const { problem, submitRes, testIndex, custom, running, submitting, code } = useStore();
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
          {submitRes!.code !== code && (
            <div className="muted small">
              You've changed the code since submitting: tests you re-run update here, the rest are from your last
              submit. Submit again to recheck them all.
            </div>
          )}
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

/** Ask, then reset one problem (or everything when id is null). */
export async function resetProblemPrompt(id: string | null, title?: string) {
  const what = id ? `“${title ?? id}”` : "ALL problems";
  if (!window.confirm(`Reset progress for ${what}?\n\nThis deletes its solved status, active time and every recorded run. It can't be undone.`)) return;
  const drafts = window.confirm(`Also delete your saved code for ${what}?\n\nOK = delete the code too · Cancel = keep the code`);
  await useStore.getState().resetProgress(id, drafts);
}
