import { useEffect, useMemo, useState } from "react";
import { useStore } from "../store";
import type { JournalEntry, Learnings as L, MistakeGroup, RunRecord } from "../types";
import { diffLines, hunks } from "../diff";
import { duration, when } from "../format";
import { md } from "./ErrorCard";
import { resetProblemPrompt } from "./Problems";

const STATUS_ICON: Record<string, string> = { pass: "✓", wrong: "✗", error: "💥", timeout: "⏱" };

export function Learnings() {
  const [data, setData] = useState<L | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [cat, setCat] = useState<string | null>(null);
  const progress = useStore((s) => s.progress); // refetch after resets
  const setView = useStore((s) => s.setView);

  const load = () =>
    fetch("/api/learnings")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Server returned ${r.status}`))))
      .then(setData, (e: Error) => setErr(e.message));
  useEffect(() => {
    load();
  }, [progress]);

  if (err) return <div className="learn"><div className="viz-hero bad">Couldn't load your history: {err}</div></div>;
  if (!data) return <div className="learn"><div className="viz-hero"><div className="spinner" /></div></div>;
  const empty = data.overview.attempted === 0;

  return (
    <div className="learn">
      <div className="learn-inner">
        <header className="learn-head">
          <button className="link" onClick={() => setView("studio")}>← Back to the studio</button>
          <h1>Your learnings</h1>
          <div className="learn-actions">
            <button className="ghost-btn" disabled={empty} onClick={() => download(data)}>⬇ Download as Markdown</button>
            <button className="ghost-btn danger" disabled={empty} onClick={() => resetProblemPrompt(null)}>Reset all progress…</button>
          </div>
        </header>
        {empty ? (
          <div className="learn-empty">
            Nothing recorded yet. Open a problem, Run and Submit: every attempt, what broke, and how long you actively
            worked on it are saved here, on this machine.
          </div>
        ) : (
          <>
            <Overview data={data} />
            <Mistakes groups={data.mistakes} onPick={setCat} picked={cat} />
            <Journal entries={data.journal} />
            <RunLog log={data.log} category={cat} onClear={() => setCat(null)} categories={data.categories} />
          </>
        )}
        <p className="muted small learn-foot">
          Stored locally in <code>{data.db_path}</code>. It survives rebuilds; nothing is sent anywhere.
        </p>
      </div>
    </div>
  );
}

function Overview({ data }: { data: L }) {
  const o = data.overview;
  const max = Math.max(1, ...o.daily.map((d) => d.minutes));
  return (
    <section className="learn-sec">
      <div className="stat-row">
        <Stat v={`${o.solved} / ${o.total}`} l="solved" />
        <Stat v={String(o.attempted)} l="attempted" />
        <Stat v={duration(o.active_seconds)} l="active time" />
        <Stat v={o.median_seconds_to_solve != null ? duration(o.median_seconds_to_solve) : "—"} l="median time to solve" />
        <Stat v={String(o.first_try)} l="solved on 1st submit" />
        <Stat v={`${o.streak} day${o.streak === 1 ? "" : "s"}`} l="streak" />
        <Stat v={`${o.runs} / ${o.submits}`} l="runs / submits" />
      </div>
      <div className="daily" title="Active minutes per day, last 30 days">
        {o.daily.map((d) => (
          <div key={d.day} className="daily-col" title={`${d.day}: ${d.minutes} min`}>
            <div className="daily-bar" style={{ height: `${(d.minutes / max) * 100}%` }} />
          </div>
        ))}
      </div>
      <div className="daily-axis muted small">
        <span>30 days ago</span>
        <span>active minutes per day</span>
        <span>today</span>
      </div>
    </section>
  );
}

function Stat({ v, l }: { v: string; l: string }) {
  return (
    <div className="stat">
      <div className="stat-v">{v}</div>
      <div className="stat-l">{l}</div>
    </div>
  );
}

function Mistakes({ groups, onPick, picked }: { groups: MistakeGroup[]; onPick: (c: string | null) => void; picked: string | null }) {
  const replay = useStore((s) => s.replay);
  if (!groups.length) {
    return (
      <section className="learn-sec">
        <h2>Your recurring mistakes</h2>
        <p className="muted">No mistakes recorded. Either you're flawless or you haven't run anything yet.</p>
      </section>
    );
  }
  const max = groups[0].count;
  return (
    <section className="learn-sec">
      <h2>Your recurring mistakes</h2>
      <p className="muted small">Each failed attempt counts once (re-running the same code doesn't). Click one to see those runs in the log.</p>
      <div className="mistakes">
        {groups.map((g) => (
          <div key={g.category} className={`mistake ${picked === g.category ? "on" : ""}`}>
            <button className="mistake-head" onClick={() => onPick(picked === g.category ? null : g.category)}>
              <span className="mistake-title">{g.title}</span>
              {g.recent && <span className="tag warn" title="Happened in the last 7 days">still happening</span>}
              <span className="mistake-count">×{g.count}</span>
            </button>
            <div className="mistake-bar"><i style={{ width: `${(g.count / max) * 100}%` }} /></div>
            <div className="mistake-lesson">💡 {md(g.lesson)}</div>
            <div className="mistake-ex">
              {g.examples.slice(0, 2).map((e) => (
                <button key={e.run_id} className="ex-run" onClick={() => replay(e.run_id)} title="Replay this run in the visualizer">
                  <span className="muted small">{g.problems.find((p) => p.id === e.problem_id)?.title} · {when(e.created_at)}</span>
                  <span>{md(e.summary ?? "")}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Journal({ entries }: { entries: JournalEntry[] }) {
  return (
    <section className="learn-sec">
      <h2>Problem journal</h2>
      <div className="journal">
        {entries.map((e) => (
          <JournalCard key={e.problem_id} e={e} />
        ))}
      </div>
    </section>
  );
}

function JournalCard({ e }: { e: JournalEntry }) {
  const { openProblem, replay } = useStore();
  const [open, setOpen] = useState(!!e.fix);
  return (
    <div className={`jcard ${e.status}`}>
      <div className="jhead">
        <span className={`p-mark ${e.status}`}>{e.status === "solved" ? "✓" : "●"}</span>
        <button className="jtitle" onClick={() => openProblem(e.problem_id)} title="Open this problem">{e.title}</button>
        <span className="muted small">{e.level}</span>
        <span className="jstats">
          ⏱ {duration(e.active_seconds)}
          {e.seconds_to_solve != null && <> · solved in {duration(e.seconds_to_solve)}</>} · {e.runs} runs · {e.submits} submits
        </span>
        <button className="link dim" onClick={() => resetProblemPrompt(e.problem_id, e.title)}>reset…</button>
      </div>
      <div className="dots">
        {e.timeline.map((t) => (
          <button
            key={t.id}
            className={`dot ${t.kind === "watch" ? "watch" : t.status} ${t.kind}`}
            title={`${t.kind} · ${when(t.created_at)}${t.summary ? ` — ${t.summary.replace(/`/g, "")}` : ""}${t.kind === "watch" ? "" : "\n(click to replay)"}`}
            onClick={() => t.kind !== "watch" && replay(t.id)}
          >
            {t.kind === "watch" ? "👁" : t.kind === "submit" ? "S" : ""}
          </button>
        ))}
      </div>
      {e.mistakes.length > 0 && <div className="jtags">{e.mistakes.map((m) => <span key={m} className="tag">{m}</span>)}</div>}
      {e.fix && (
        <div className="fix">
          <button className="fix-toggle" onClick={() => setOpen(!open)}>
            {open ? "▾" : "▸"} What fixed it
          </button>
          {open && (
            <>
              {e.fix.summary && (
                <div className="fix-why">
                  <b>Before:</b> {md(e.fix.summary)}
                </div>
              )}
              <Diff before={e.fix.before} after={e.fix.after} />
              <div className="row-btns">
                <button className="link" onClick={() => replay(e.fix!.before_run)}>⏪ replay the broken version</button>
                <button className="link" onClick={() => replay(e.fix!.after_run)}>▶ replay the fix</button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function Diff({ before, after }: { before: string; after: string }) {
  const lines = useMemo(() => hunks(diffLines(before, after)), [before, after]);
  if (!lines.some((l) => l && l.t !== "same")) return <div className="muted small">No code change (it passed on a re-submit).</div>;
  return (
    <pre className="diff-view">
      {lines.map((l, k) =>
        l === null ? (
          <div key={k} className="d-gap">⋯</div>
        ) : (
          <div key={k} className={`d-${l.t}`}>
            <span className="d-sign">{l.t === "add" ? "+" : l.t === "del" ? "−" : " "}</span>
            {l.text || " "}
          </div>
        ),
      )}
    </pre>
  );
}

function RunLog({ log, category, onClear, categories }: { log: RunRecord[]; category: string | null; onClear: () => void; categories: L["categories"] }) {
  const { replay, restore } = useStore();
  const [status, setStatus] = useState("all");
  const [problem, setProblem] = useState("all");
  const problems = useMemo(() => [...new Map(log.map((r) => [r.problem_id, r.title_problem ?? r.problem_id])).entries()], [log]);
  const rows = log.filter(
    (r) =>
      (status === "all" || (status === "failed" ? r.status !== "pass" && r.kind !== "watch" : r.status === status)) &&
      (problem === "all" || r.problem_id === problem) &&
      (!category || r.category === category),
  );
  return (
    <section className="learn-sec">
      <h2>Run log</h2>
      <div className="log-filters">
        <select className="speed" value={problem} onChange={(e) => setProblem(e.target.value)}>
          <option value="all">all problems</option>
          {problems.map(([id, t]) => (
            <option key={id} value={id}>{t}</option>
          ))}
        </select>
        <select className="speed" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">all results</option>
          <option value="failed">failed only</option>
          <option value="pass">passed</option>
          <option value="wrong">wrong answer</option>
          <option value="error">crashed</option>
          <option value="timeout">too slow</option>
        </select>
        {category && (
          <button className="tag on" onClick={onClear}>{categories[category]?.title ?? category} ✕</button>
        )}
        <span className="muted small">{rows.length} of {log.length}</span>
      </div>
      <table className="runlog">
        <thead>
          <tr>
            <th>when</th>
            <th>problem</th>
            <th>kind</th>
            <th>result</th>
            <th>what went wrong</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className={r.kind === "watch" ? "watch" : r.status}>
              <td className="nowrap muted">{when(r.created_at)}</td>
              <td className="nowrap">{r.title_problem}</td>
              <td className="muted">{r.kind}{r.kind === "run" && r.test_index != null ? ` · test ${r.test_index + 1}` : r.custom_input != null ? " · custom" : ""}</td>
              <td className={`nowrap res-${r.status}`}>
                {r.kind === "watch" ? "👁 watched" : `${STATUS_ICON[r.status]} ${r.status}`}
                {r.kind === "submit" && r.total ? ` (${r.passed}/${r.total})` : ""}
              </td>
              <td>
                {r.category && <span className="tag">{categories[r.category]?.title ?? r.category}</span>}{" "}
                {r.summary && md(r.summary)}
                {r.line ? <span className="muted small"> · line {r.line}</span> : null}
              </td>
              <td className="nowrap">
                {r.kind !== "watch" && (
                  <>
                    <button className="link" onClick={() => replay(r.id)}>replay</button>{" "}
                    <button className="link dim" onClick={() => window.confirm("Replace your current code for this problem with this run's code?") && restore(r.id)}>restore</button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function download(data: L) {
  const o = data.overview;
  const out: string[] = [
    "# WhyDidItBreak learnings",
    "",
    `Exported ${new Date().toLocaleString()}.`,
    "",
    `- Solved **${o.solved} / ${o.total}**, attempted ${o.attempted}`,
    `- Active time ${duration(o.active_seconds)}; median time to solve ${o.median_seconds_to_solve != null ? duration(o.median_seconds_to_solve) : "—"}`,
    `- Solved on the first submit: ${o.first_try}; streak: ${o.streak} day(s)`,
    "",
    "## Recurring mistakes",
    "",
  ];
  for (const g of data.mistakes) {
    out.push(`### ${g.title} (×${g.count})`, "", `> ${g.lesson}`, "", `Problems: ${g.problems.map((p) => p.title).join(", ")}`, "");
    for (const e of g.examples) out.push(`- ${e.summary ?? ""}${e.line ? ` (line ${e.line})` : ""}`);
    out.push("");
  }
  out.push("## Problem journal", "");
  for (const e of data.journal) {
    out.push(
      `### ${e.status === "solved" ? "✅" : "⏳"} ${e.title}`,
      "",
      `Active ${duration(e.active_seconds)}${e.seconds_to_solve != null ? `, solved in ${duration(e.seconds_to_solve)}` : ""}; ${e.runs} runs, ${e.submits} submits.`,
      "",
    );
    if (e.mistakes.length) out.push(`Mistakes: ${e.mistakes.join(", ")}`, "");
    if (e.fix) {
      out.push(`What went wrong: ${e.fix.summary ?? e.fix.title ?? ""}`, "", "```diff");
      for (const l of hunks(diffLines(e.fix.before, e.fix.after))) out.push(l === null ? "…" : `${l.t === "add" ? "+" : l.t === "del" ? "-" : " "} ${l.text}`);
      out.push("```", "");
    }
  }
  const blob = new Blob([out.join("\n")], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `whydidbreak-learnings-${new Date().toLocaleDateString("en-CA")}.md`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
