import { create } from "zustand";
import type { Lesson, LessonInfo, RunResult } from "./types";

const DEFAULT_CODE = `# Welcome to WhyDidItBreak!
# Write Python, press Run (Ctrl/Cmd+Enter), then step through it.
# Try a lesson from the left, or break this code on purpose.

a = [5, 1, 4, 2, 8, 3]
n = len(a)
for i in range(n):
    for j in range(n - 1 - i):
        if a[j] > a[j + 1]:
            a[j], a[j + 1] = a[j + 1], a[j]
print(a)
`;

function load(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable */
  }
}

interface State {
  code: string;
  res: RunResult | null;
  step: number;
  playing: boolean;
  speed: number; // ms per step
  running: boolean;
  netError: string | null;
  dirty: boolean; // code changed since last run
  lessons: LessonInfo[];
  levels: string[];
  lesson: Lesson | null;
  variant: "code" | "buggy" | null;
  showLessons: boolean;
  hoverLine: number | null;

  setCode: (c: string) => void;
  run: () => Promise<void>;
  setStep: (i: number) => void;
  stepBy: (d: number) => void;
  togglePlay: () => void;
  setSpeed: (ms: number) => void;
  fetchLessons: () => Promise<void>;
  openLesson: (id: string, variant: "code" | "buggy") => Promise<void>;
  toggleLessons: () => void;
  setHoverLine: (l: number | null) => void;
}

export const useStore = create<State>((set, get) => ({
  code: load("wdib.code", DEFAULT_CODE),
  res: null,
  step: 0,
  playing: false,
  speed: 450,
  running: false,
  netError: null,
  dirty: true,
  lessons: [],
  levels: [],
  lesson: null,
  variant: null,
  showLessons: load("wdib.lessons", "1") === "1",
  hoverLine: null,

  setCode: (c) => {
    save("wdib.code", c);
    set({ code: c, dirty: true });
  },

  run: async () => {
    set({ running: true, playing: false, netError: null });
    try {
      const r = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: get().code }),
      });
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      const res = (await r.json()) as RunResult;
      // land on the crash when there is one, otherwise start at the beginning
      const start = res.error?.step ?? 0;
      set({ res, step: Math.max(0, Math.min(start, res.steps.length - 1)), dirty: false });
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
  setSpeed: (ms) => set({ speed: ms }),

  fetchLessons: async () => {
    try {
      const r = await fetch("/api/lessons");
      const j = await r.json();
      set({ lessons: j.lessons, levels: j.levels });
    } catch {
      /* server offline: netError will show on run */
    }
  },

  openLesson: async (id, variant) => {
    const r = await fetch(`/api/lessons/${id}`);
    const lesson = (await r.json()) as Lesson;
    const code = variant === "buggy" ? lesson.buggy : lesson.code;
    save("wdib.code", code);
    set({ lesson, variant, code, res: null, step: 0, playing: false, dirty: true });
    await get().run();
  },

  toggleLessons: () => {
    const v = !get().showLessons;
    save("wdib.lessons", v ? "1" : "0");
    set({ showLessons: v });
  },
  setHoverLine: (l) => set({ hoverLine: l }),
}));
