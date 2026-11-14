import type { ReactNode } from "react";
import type { ErrorInfo, Frame, Heap, Meta, Op, RunResult, Step } from "../types";
import type { Scene, SceneKind } from "../detect";
import { KIND_LABEL, alternatives } from "../detect";
import { colorFor } from "../trace";

export interface Ctx {
  res: RunResult;
  i: number;
  step: Step;
  frames: Frame[];
  heap: Heap;
  meta: Meta;
  error: ErrorInfo | null;
  atError: boolean; // current step is the crash step
}

export const C = {
  bar: "#3b4a6b",
  barTop: "#5b6f9c",
  cmp: "#fbbf24",
  read: "#38bdf8",
  write: "#f472b6",
  ok: "#34d399",
  bad: "#f43f5e",
  dim: "#64748b",
  text: "#e2e8f0",
  sub: "#94a3b8",
  panel: "#121a2e",
  edge: "#475569",
};

export function opsFor(step: Step, oid?: string): Op[] {
  if (!oid) return [];
  return step.ops.filter((o) => o.oid === oid);
}

export function SceneFrame({
  scene,
  children,
  onOverride,
  extra,
}: {
  scene: Scene;
  children: ReactNode;
  onOverride?: (name: string, kind: SceneKind | null) => void;
  extra?: ReactNode;
}) {
  const alts = scene.obj ? alternatives(scene.obj) : [];
  return (
    <section className="scene">
      <header className="scene-head">
        <span className="scene-names">
          {scene.names.length === 0 && <span className="scene-name">{KIND_LABEL[scene.kind]}</span>}
          {scene.names.map((n, k) => (
            <span key={n} className="scene-name" style={{ color: k === 0 ? undefined : C.sub }}>
              {k > 0 && <span className="eq">=</span>}
              {n}
            </span>
          ))}
        </span>
        {scene.names.length > 0 && <span className="scene-kind">{KIND_LABEL[scene.kind]}</span>}
        {extra}
        {onOverride && alts.length > 1 && (
          <select
            className="scene-select"
            value={scene.kind}
            title="Draw this variable as…"
            onChange={(e) => onOverride(scene.names[0], e.target.value as SceneKind)}
          >
            {alts.map((k) => (
              <option key={k} value={k}>
                {KIND_LABEL[k]}
              </option>
            ))}
          </select>
        )}
      </header>
      <div className="scene-body">{children}</div>
    </section>
  );
}

/** A labelled arrow pointing up at x (used under arrays). */
export function PointerTag({ x, y, name, value, bad }: { x: number; y: number; name: string; value?: string; bad?: boolean }) {
  const col = bad ? C.bad : colorFor(name);
  const text = value !== undefined ? `${name}=${value}` : name;
  const w = Math.max(22, text.length * 7 + 10);
  return (
    <g style={{ transform: `translate(${x}px, ${y}px)`, transition: "transform 0.35s cubic-bezier(.2,.8,.2,1)" }}>
      <path d="M0,0 L-5,8 L5,8 Z" fill={col} />
      <rect x={-w / 2} y={9} width={w} height={17} rx={8.5} fill={col} opacity={0.18} stroke={col} strokeWidth={1} />
      <text x={0} y={21.5} textAnchor="middle" fontSize={11} fontWeight={600} fill={col} fontFamily="var(--mono)">
        {text}
      </text>
    </g>
  );
}

export function Empty({ text }: { text: string }) {
  return <div className="viz-empty">{text}</div>;
}
