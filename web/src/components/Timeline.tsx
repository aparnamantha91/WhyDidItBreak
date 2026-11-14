import { useEffect, useRef, useState } from "react";
import { useStore } from "../store";

/** Scrubbable timeline: call-depth sparkline + event ticks + crash marker. */
export function Timeline() {
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  const setStep = useStore((s) => s.setStep);
  const canvas = useRef<HTMLCanvasElement>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [w, setW] = useState(600);
  const dragging = useRef(false);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const n = res?.steps.length ?? 0;
  useEffect(() => {
    const c = canvas.current;
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const H = 34;
    c.width = w * dpr;
    c.height = H * dpr;
    const g = c.getContext("2d")!;
    g.scale(dpr, dpr);
    g.clearRect(0, 0, w, H);
    g.fillStyle = "#0e1527";
    g.fillRect(0, 0, w, H);
    if (!res || !n) return;
    const xOf = (k: number) => (n === 1 ? w / 2 : (k / (n - 1)) * (w - 2) + 1);
    // depth sparkline
    const depths = res.steps.map((s) => (res.pool[s.frames] as number[]).length);
    const maxD = Math.max(1, ...depths);
    g.beginPath();
    g.moveTo(0, H);
    res.steps.forEach((_, k) => g.lineTo(xOf(k), H - 4 - ((depths[k] - 1) / Math.max(1, maxD - 1)) * (H - 12) * (maxD > 1 ? 1 : 0)));
    g.lineTo(w, H);
    g.closePath();
    g.fillStyle = "rgba(99,102,241,0.22)";
    g.fill();
    // ticks
    res.steps.forEach((s, k) => {
      let col: string | null = null;
      if (s.ev === "exception") col = "#f43f5e";
      else if (s.ops.some((o) => o.k === "swap")) col = "#34d399";
      else if (s.ev === "call" && s.fn !== "global") col = "#a78bfa";
      if (col) {
        g.fillStyle = col;
        g.fillRect(xOf(k) - 0.5, s.ev === "exception" ? 0 : H - 8, Math.max(1, w / n / 2), s.ev === "exception" ? H : 8);
      }
    });
    // played region
    g.fillStyle = "rgba(56,189,248,0.10)";
    g.fillRect(0, 0, xOf(i), H);
    // crash marker
    if (res.error?.step !== undefined) {
      const x = xOf(res.error.step);
      g.fillStyle = "#f43f5e";
      g.beginPath();
      g.moveTo(x - 6, 0);
      g.lineTo(x + 6, 0);
      g.lineTo(x, 8);
      g.fill();
    }
    // cursor
    g.fillStyle = "#38bdf8";
    g.fillRect(xOf(i) - 1, 0, 2, H);
  }, [res, i, w, n]);

  const at = (e: React.PointerEvent) => {
    const r = wrap.current!.getBoundingClientRect();
    return Math.round(((e.clientX - r.left) / r.width) * (n - 1));
  };

  return (
    <div
      className="timeline"
      ref={wrap}
      onPointerDown={(e) => {
        if (!n) return;
        dragging.current = true;
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        setStep(at(e));
      }}
      onPointerMove={(e) => {
        if (!n) return;
        setHover(at(e));
        if (dragging.current) setStep(at(e));
      }}
      onPointerUp={() => (dragging.current = false)}
      onPointerLeave={() => setHover(null)}
    >
      <canvas ref={canvas} style={{ width: "100%", height: 34, display: "block" }} />
      {hover !== null && res && res.steps[hover] && (
        <div className="tl-tip" style={{ left: `${(hover / Math.max(1, n - 1)) * 100}%` }}>
          step {hover + 1} · line {res.steps[hover].line}
          {res.steps[hover].ev !== "line" ? ` · ${res.steps[hover].ev}` : ""}
        </div>
      )}
    </div>
  );
}
