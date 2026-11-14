import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useStore } from "../store";
import { detectScenes, pointerNames, type Scene, type SceneKind } from "../detect";
import { colorFor, show, snapshot, visibleVars } from "../trace";
import type { Ctx } from "../viz/common";
import { SceneFrame } from "../viz/common";
import { ArrayView } from "../viz/ArrayView";
import { GridView } from "../viz/GridView";
import { HashView } from "../viz/HashView";
import { StackQueueView } from "../viz/StackQueueView";
import { HeapView } from "../viz/HeapView";
import { GraphView } from "../viz/GraphView";
import { LinkedView } from "../viz/LinkedView";
import { TreeView } from "../viz/TreeView";
import { ObjectView } from "../viz/ObjectView";
import { CallTree } from "../viz/CallTree";
import { ErrorCard } from "./ErrorCard";
import { VerdictCard } from "./VerdictCard";

function SceneBody({ ctx, scene }: { ctx: Ctx; scene: Scene }) {
  switch (scene.kind) {
    case "bars":
    case "cells":
      return <ArrayView ctx={ctx} scene={scene} />;
    case "grid":
      return <GridView ctx={ctx} scene={scene} />;
    case "hash":
      return <HashView ctx={ctx} scene={scene} />;
    case "stack":
    case "queue":
      return <StackQueueView ctx={ctx} scene={scene} />;
    case "heap":
      return <HeapView ctx={ctx} scene={scene} />;
    case "graph":
      return <GraphView ctx={ctx} scene={scene} />;
    case "linked":
      return <LinkedView ctx={ctx} scene={scene} />;
    case "tree":
      return <TreeView ctx={ctx} scene={scene} />;
    case "object":
      return <ObjectView ctx={ctx} scene={scene} />;
  }
}

export function Visualizer() {
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  const running = useStore((s) => s.running);
  const netError = useStore((s) => s.netError);
  const setStep = useStore((s) => s.setStep);
  const problem = useStore((s) => s.problem);
  const [overrides, setOverrides] = useState<Record<string, SceneKind>>({});

  const ctx: Ctx | null = useMemo(() => {
    if (!res || !res.steps.length) return null;
    const step = res.steps[i];
    const { frames, heap } = snapshot(res, i);
    const atError = !!res.error && res.error.step === i;
    return { res, i, step, frames, heap, meta: res.meta, error: res.error, atError };
  }, [res, i]);

  if (netError) return <div className="viz-hero bad">{netError}</div>;
  if (!res) {
    return (
      <div className="viz-hero">
        {running ? (
          <div className="spinner" />
        ) : (
          <>
            <div className="hero-title">{problem ? `Solve “${problem.title}”, then press ▶ Run` : "Press ▶ Run to trace your code"}</div>
            <div className="muted">
              {problem
                ? "Run traces your function on one test. Submit checks them all and shows you where it breaks."
                : "Every step, every pointer, every swap — and exactly where it breaks."}
            </div>
            <div className="hero-keys">
              <kbd>⌘/Ctrl</kbd>+<kbd>Enter</kbd> run · <kbd>←</kbd>
              <kbd>→</kbd> step · <kbd>Space</kbd> play
            </div>
          </>
        )}
      </div>
    );
  }
  if (!ctx) {
    return (
      <div className="viz-scroll">
        <VerdictCard />
        {res.error && <ErrorCard error={res.error} atError total={0} />}
      </div>
    );
  }

  const scenes = detectScenes(ctx.frames, ctx.heap, ctx.meta, overrides);
  const showCalls = (ctx.meta.recursive?.length ?? 0) > 0;

  return (
    <div className="viz-scroll">
      <VerdictCard />
      {res.error && <ErrorCard error={res.error} atError={ctx.atError} total={res.steps.length} />}
      <VarChips ctx={ctx} />
      <AnimatePresence initial={false}>
        {scenes.map((sc) => (
          <motion.div key={sc.key} layout="position" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <SceneFrame
              scene={sc}
              onOverride={(name, kind) =>
                setOverrides((o) => {
                  const n = { ...o };
                  if (kind) n[name] = kind;
                  else delete n[name];
                  return n;
                })
              }
            >
              <SceneBody ctx={ctx} scene={sc} />
            </SceneFrame>
          </motion.div>
        ))}
      </AnimatePresence>
      {showCalls && (
        <section className="scene">
          <header className="scene-head">
            <span className="scene-name">Call tree</span>
            <span className="scene-kind">recursion · click a call to jump there</span>
          </header>
          <div className="scene-body">
            <CallTree res={res} i={i} onJump={setStep} />
          </div>
        </section>
      )}
      {scenes.length === 0 && !showCalls && <div className="muted center pad">No data structures in scope yet.</div>}
    </div>
  );
}

function VarChips({ ctx }: { ctx: Ctx }) {
  const vars = visibleVars(ctx.frames).filter(([, v]) => v.t !== "ref");
  if (!vars.length) return null;
  const changed = new Set(ctx.step.ops.filter((o) => o.k === "assign" || o.k === "new").map((o) => o.var));
  const old = new Map(ctx.step.ops.filter((o) => o.k === "assign").map((o) => [o.var, o.old]));
  const culprits = new Set(ctx.atError ? ctx.error?.culprits.map((c) => c.name) : []);
  const frozen = new Set(ctx.atError ? ctx.error?.viz?.frozen ?? [] : []);
  const ptr = new Set(pointerNames(Object.keys(ctx.meta.index_vars ?? {}), ctx.meta));
  const local = ctx.frames.length > 1 ? ctx.frames[ctx.frames.length - 1].fn : null;
  return (
    <div className="chips">
      {local && <span className="chip-scope">in {local}()</span>}
      {vars.map(([name, v, isGlobal]) => {
        const hot = changed.has(name);
        const bad = culprits.has(name);
        return (
          <motion.span
            key={`${name}${hot ? `@${ctx.i}` : ""}`}
            className={`var-chip ${bad ? "bad" : ""} ${isGlobal && local ? "global" : ""}`}
            initial={hot ? { scale: 1.18, backgroundColor: "rgba(244,114,182,0.35)" } : false}
            animate={{ scale: 1, backgroundColor: "rgba(27,37,64,1)" }}
            transition={{ duration: 0.45 }}
            title={old.has(name) ? `was ${old.get(name)}` : undefined}
          >
            {ptr.has(name) && <span className="legend-dot" style={{ background: colorFor(name) }} />}
            <span className="vc-name">{name}</span>
            <span className="vc-val">{show(v, ctx.heap)}</span>
            {old.has(name) && <span className="vc-old">{old.get(name)}</span>}
            {frozen.has(name) && <span title="never changed">❄</span>}
          </motion.span>
        );
      })}
    </div>
  );
}
