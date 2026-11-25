import { useStore } from "./store";

const IDLE_AFTER = 60_000; // no input for a minute = not active
const REPORT_EVERY = 15; // seconds

let lastInput = Date.now();
let started = false;

function active(): boolean {
  const s = useStore.getState();
  return (
    document.visibilityState === "visible" &&
    document.hasFocus() &&
    Date.now() - lastInput < IDLE_AFTER &&
    s.view === "studio" &&
    !!s.problem &&
    s.progress[s.problem.id]?.status !== "solved" // the clock stops once the problem is solved
  );
}

function flush(beacon = false) {
  const s = useStore.getState();
  const seconds = s.pendingActive;
  if (!seconds || !s.problem) return;
  const body = JSON.stringify({ problem_id: s.problem.id, seconds });
  useStore.setState({ pendingActive: 0 });
  // the server adds the report to the stored total; show that total afterwards
  const done = () => {
    const row = useStore.getState().progress[s.problem!.id];
    if (row) {
      useStore.setState({
        progress: { ...useStore.getState().progress, [row.problem_id]: { ...row, active_seconds: row.active_seconds + seconds } },
      });
    } else useStore.getState().refreshProgress();
  };
  if (beacon && navigator.sendBeacon) {
    navigator.sendBeacon("/api/activity", new Blob([body], { type: "application/json" }));
    done();
    return;
  }
  fetch("/api/activity", { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true })
    .then(done)
    .catch(() => useStore.setState({ pendingActive: useStore.getState().pendingActive + seconds }));
}

/** Counts seconds of real work on the open problem and reports them to the server. */
export function startActivityTracking() {
  if (started) return;
  started = true;
  const touch = () => (lastInput = Date.now());
  for (const ev of ["keydown", "pointerdown", "pointermove", "wheel", "scroll"]) {
    window.addEventListener(ev, touch, { passive: true, capture: true });
  }
  // stepping through a trace counts as working, even with the keyboard idle
  useStore.subscribe((s, prev) => {
    if (s.step !== prev.step || s.code !== prev.code) touch();
    if (s.problem?.id !== prev.problem?.id && prev.problem) {
      // switching problems: report the time to the problem it belongs to
      const seconds = prev.pendingActive;
      if (seconds) {
        useStore.setState({ pendingActive: 0 });
        fetch("/api/activity", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ problem_id: prev.problem.id, seconds }),
        }).catch(() => {});
      }
    }
  });
  setInterval(() => {
    if (!active()) return;
    const n = useStore.getState().pendingActive + 1;
    useStore.setState({ pendingActive: n });
    if (n >= REPORT_EVERY) flush();
  }, 1000);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flush(true);
  });
  window.addEventListener("pagehide", () => flush(true));
}
