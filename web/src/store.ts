import { create } from "zustand";
import type { Problem, ProblemInfo, ProgressRow, RunResult, SubmitResult } from "./types";

const DEFAULT_CODE = `# Playground: write any Python, press Run (Ctrl/Cmd+Enter), then step through it.
# Pick a problem on the left when you want something to solve.

a = [5, 1, 4, 2, 8, 3]
n = len(a)
for i in range(n):
    for j in range(n - 1 - i):
        if a[j] > a[j + 1]:
            a[j], a[j + 1] = a[j + 1], a[j]
print(a)
`;

export function load(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

export function save(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* storage unavailable */
  }
}

function loadJson<T>(key: string, fallback: T): T {
  try {
    return JSON.parse(load(key, "")) as T;
  } catch {
    return fallback;
  }
}

export type Tab = "desc" | "tests" | "sample" | "solution";
export type Progress = Record<string, ProgressRow>;
export type View = "studio" | "learnings";
/** Reference (or old) code being watched read-only; the user's own draft is left untouched. */
export interface Viewing {
  kind: "sample" | "buggy" | "solution" | "replay";
  code: string;
  label: string;
}

let inited = false;
let draftTimer: ReturnType<typeof setTimeout> | undefined;
const json = { "Content-Type": "application/json" };

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) throw new Error(`Server returned ${r.status}`);
  return (await r.json()) as T;
}

/** Older versions kept progress and drafts in this browser only; move them into the database once. */
async function importLocalStorage() {
  if (load("wdib.imported", "") === "1") return;
  const progress = loadJson<Record<string, string>>("wdib.progress", {});
  const drafts: Record<string, string> = {};
  try {
    for (let k = 0; k < localStorage.length; k++) {
      const key = localStorage.key(k)!;
      if (key.startsWith("wdib.draft.")) drafts[key.slice("wdib.draft.".length)] = localStorage.getItem(key) ?? "";
    }
  } catch {
    /* storage unavailable */
  }
  if (Object.keys(progress).length || Object.keys(drafts).length) {
    await api("/api/import", { method: "POST", headers: json, body: JSON.stringify({ progress, drafts }) });
  }
  save("wdib.imported", "1");
}
const draftKey = (id: string | undefined) => (id ? `wdib.draft.${id}` : "wdib.code");

interface State {
  code: string; // the user's own code (draft for the open problem, or the playground)
  res: RunResult | null;
  step: number;
  playing: boolean;
  speed: number; // ms per step
  running: boolean;
  netError: string | null;
  dirty: boolean; // code changed since last run

  problems: ProblemInfo[];
  levels: string[];
  companies: string[]; // every company that asks any problem, indexed by ProblemInfo.companies
  problem: Problem | null; // null = playground
  progress: Progress;
  showPanel: boolean;
  showList: boolean;
  tab: Tab;
  testIndex: number; // -1 = custom input
  custom: string;
  submitRes: SubmitResult | null;
  submitting: boolean;
  viewing: Viewing | null;
  hoverLine: number | null;
  view: View;
  pendingActive: number; // active seconds not yet reported to the server

  setCode: (c: string) => void;
  run: () => Promise<void>;
  setStep: (i: number) => void;
  stepBy: (d: number) => void;
  togglePlay: () => void;
  setSpeed: (ms: number) => void;
  init: () => Promise<void>;
  openProblem: (id: string) => Promise<void>;
  openPlayground: () => void;
  resetCode: () => void;
  setTab: (t: Tab) => void;
  setShowList: (v: boolean) => void;
  setTest: (i: number) => void;
  setCustom: (s: string) => void;
  runTest: (i: number) => Promise<void>;
  submit: () => Promise<void>;
  watch: (kind: Viewing["kind"]) => Promise<void>;
  stopWatching: () => void;
  togglePanel: () => void;
  setHoverLine: (l: number | null) => void;
  refreshProgress: () => Promise<void>;
  resetProgress: (problemId: string | null, drafts: boolean) => Promise<void>;
  setView: (v: View) => void;
  replay: (runId: number) => Promise<void>;
  restore: (runId: number) => Promise<void>;
}

export const useStore = create<State>((set, get) => ({
  code: load("wdib.code", DEFAULT_CODE),
  res: null,
  step: 0,
  playing: false,
  speed: Number(load("wdib.speed", "450")) || 450,
  running: false,
  netError: null,
  dirty: true,

  problems: [],
  levels: [],
  companies: [],
  problem: null,
  progress: {},
  showPanel: load("wdib.panel", "1") === "1",
  showList: true,
  tab: "desc",
  testIndex: 0,
  custom: "",
  submitRes: null,
  submitting: false,
  viewing: null,
  hoverLine: null,
  view: location.hash === "#/learnings" ? "learnings" : "studio",
  pendingActive: 0,

  setCode: (c) => {
    if (get().viewing) return; // reference code is read-only
    const id = get().problem?.id;
    set({ code: c, dirty: true });
    if (!id) {
      save("wdib.code", c); // the playground stays in this browser
      return;
    }
    clearTimeout(draftTimer);
    draftTimer = setTimeout(() => {
      fetch(`/api/drafts/${id}`, { method: "PUT", headers: json, body: JSON.stringify({ code: c }) }).catch(() => {});
    }, 800);
  },

  run: async () => {
    const { viewing, problem, testIndex, custom, code } = get();
    set({ running: true, playing: false, netError: null });
    try {
      const body: Record<string, unknown> = { code: viewing ? viewing.code : code };
      if (viewing) body.watch = viewing.kind;
      // lesson samples are whole programs; everything else in problem mode is judged on a test case
      if (problem && (!viewing || viewing.kind === "solution" || viewing.kind === "replay")) {
        body.problem_id = problem.id;
        if (testIndex < 0) body.custom = custom;
        else body.test = testIndex;
      } else if (problem) body.watch_problem = problem.id;
      const r = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.status === 400) {
        const j = await r.json();
        set({ res: null, netError: `Custom input: ${j.detail}` });
        return;
      }
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      const res = (await r.json()) as RunResult;
      // land on the crash when there is one, otherwise start at the beginning
      const start = res.error?.step ?? 0;
      set({ res, step: Math.max(0, Math.min(start, res.steps.length - 1)), dirty: false });
      // re-running one test after a submit updates that test's row, so a fix shows up without resubmitting
      const sub = get().submitRes;
      if (problem && !viewing && testIndex >= 0 && res.verdict && sub && !sub.fatal) {
        const results = sub.results.map((row) => (row.index === testIndex ? { ...res.verdict!, index: testIndex } : row));
        set({ submitRes: { ...sub, results, passed: results.filter((x) => x.status === "pass").length } });
      }
      if (problem && !viewing) get().refreshProgress();
    } catch (e) {
      set({ netError: `Couldn't reach the Python server (${(e as Error).message}). Is it running on :8000?` });
    } finally {
      set({ running: false });
    }
  },

  setStep: (i) => {
    const n = get().res?.steps.length ?? 0;
    set({ step: Math.max(0, Math.min(i, n - 1)) });
  },
  stepBy: (d) => get().setStep(get().step + d),
  togglePlay: () => {
    const { playing, res, step } = get();
    if (!res) return;
    if (!playing && step >= res.steps.length - 1) set({ step: 0 });
    set({ playing: !playing });
  },
  setSpeed: (ms) => {
    save("wdib.speed", String(ms));
    set({ speed: ms });
  },

  init: async () => {
    if (inited) return; // once per page load: re-opening the saved problem later would wipe live state
    inited = true;
    try {
      const j = await api<{ problems: ProblemInfo[]; levels: string[]; companies: string[] }>("/api/problems");
      set({ problems: j.problems, levels: j.levels, companies: j.companies });
      try {
        const p = await api<{ empty: boolean }>("/api/progress");
        if (p.empty) await importLocalStorage();
        else save("wdib.imported", "1");
      } catch {
        /* keep going without history */
      }
      await get().refreshProgress();
      const last = load("wdib.problem", "");
      if (last && (j.problems as ProblemInfo[]).some((p) => p.id === last)) await get().openProblem(last);
    } catch {
      /* server offline: netError will show on run */
    }
  },

  openProblem: async (id) => {
    const r = await fetch(`/api/problems/${id}`);
    if (!r.ok) return;
    const problem = (await r.json()) as Problem;
    save("wdib.problem", id);
    clearTimeout(draftTimer);
    let draft: string | null = null;
    try {
      draft = (await api<{ code: string | null }>(`/api/drafts/${id}`)).code;
    } catch {
      draft = null;
    }
    fetch(`/api/progress/${id}/open`, { method: "POST" }).then(() => get().refreshProgress(), () => {});
    set({
      problem,
      view: "studio",
      code: draft ?? load(draftKey(id), problem.starter),
      res: null,
      step: 0,
      playing: false,
      dirty: true,
      netError: null,
      showList: false,
      tab: "desc",
      testIndex: 0,
      custom: "",
      submitRes: null,
      viewing: null,
    });
  },

  openPlayground: () => {
    save("wdib.problem", null);
    set({
      problem: null,
      code: load("wdib.code", DEFAULT_CODE),
      res: null,
      step: 0,
      playing: false,
      dirty: true,
      netError: null,
      submitRes: null,
      viewing: null,
    });
  },

  resetCode: () => {
    const { problem } = get();
    const code = problem ? problem.starter : DEFAULT_CODE;
    if (problem) {
      clearTimeout(draftTimer);
      fetch(`/api/drafts/${problem.id}`, { method: "PUT", headers: json, body: JSON.stringify({ code }) }).catch(() => {});
    } else save("wdib.code", code);
    set({ code, dirty: true, viewing: null, res: null, submitRes: null });
  },

  setTab: (tab) => set({ tab }),
  setShowList: (showList) => set({ showList }),
  setTest: (testIndex) => set({ testIndex, dirty: true }),
  setCustom: (custom) => set({ custom, dirty: get().testIndex < 0 ? true : get().dirty }),
  runTest: async (i) => {
    set({ testIndex: i });
    await get().run();
  },

  submit: async () => {
    const { problem, code } = get();
    if (!problem) return;
    set({ submitting: true, viewing: null, playing: false, netError: null });
    try {
      const r = await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, problem_id: problem.id }),
      });
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      const submitRes = { ...((await r.json()) as SubmitResult), code };
      await get().refreshProgress();
      set({ submitRes, tab: "tests", showPanel: true, showList: false });
      // go straight to the first case that broke, so there is something to debug
      const bad = submitRes.results.find((x) => x.status !== "pass" && x.status !== "skipped");
      await get().runTest(bad ? bad.index : Math.max(0, get().testIndex));
    } catch (e) {
      set({ netError: `Couldn't reach the Python server (${(e as Error).message}). Is it running on :8000?` });
    } finally {
      set({ submitting: false });
    }
  },

  watch: async (kind) => {
    const { problem } = get();
    if (!problem) return;
    const lesson = problem.lesson;
    if (kind !== "solution" && !lesson) return;
    const viewing: Viewing =
      kind === "solution"
        ? { kind, code: problem.solution, label: `Reference solution for “${problem.title}”` }
        : kind === "buggy"
          ? { kind, code: lesson!.buggy, label: `Sample with a bug: ${lesson!.title}` }
          : { kind, code: lesson!.code, label: `Sample code: ${lesson!.title}` };
    set({ viewing, res: null, step: 0 });
    await get().run();
  },
  stopWatching: () => set({ viewing: null, res: null, step: 0, playing: false, dirty: true }),

  togglePanel: () => {
    const v = !get().showPanel;
    save("wdib.panel", v ? "1" : "0");
    set({ showPanel: v });
  },
  setHoverLine: (l) => set({ hoverLine: l }),

  refreshProgress: async () => {
    try {
      const p = await api<{ problems: Progress }>("/api/progress");
      set({ progress: p.problems });
    } catch {
      /* server offline */
    }
  },

  resetProgress: async (problemId, drafts) => {
    await api(problemId ? `/api/progress/${problemId}?drafts=${drafts}` : `/api/progress?drafts=${drafts}`, {
      method: "DELETE",
    });
    const { problem } = get();
    if (drafts && problem && (!problemId || problemId === problem.id)) {
      set({ code: problem.starter, res: null, submitRes: null, viewing: null, dirty: true });
    }
    if (!problemId || problemId === problem?.id) set({ submitRes: null });
    await get().refreshProgress();
  },

  setView: (view) => {
    const hash = view === "learnings" ? "#/learnings" : "";
    if (location.hash !== hash) history.pushState(null, "", hash || location.pathname);
    set({ view, playing: false });
  },

  replay: async (runId) => {
    const run = await api<import("./types").RunRecord>(`/api/runs/${runId}`);
    if (get().problem?.id !== run.problem_id) await get().openProblem(run.problem_id);
    const when = new Date(run.created_at).toLocaleString();
    set({
      view: "studio",
      showPanel: true,
      testIndex: run.custom_input != null ? -1 : (run.test_index ?? 0),
      custom: run.custom_input ?? get().custom,
      viewing: { kind: "replay", code: run.code ?? "", label: `Your ${run.kind} from ${when}` },
      res: null,
      step: 0,
    });
    if (location.hash) history.pushState(null, "", location.pathname);
    await get().run();
  },

  restore: async (runId) => {
    const run = await api<import("./types").RunRecord>(`/api/runs/${runId}`);
    if (get().problem?.id !== run.problem_id) await get().openProblem(run.problem_id);
    set({ viewing: null, view: "studio" });
    get().setCode(run.code ?? "");
    set({ res: null, submitRes: null });
    if (location.hash) history.pushState(null, "", location.pathname);
  },
}));
