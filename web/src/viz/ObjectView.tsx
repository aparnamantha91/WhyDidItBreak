import type { Scene } from "../detect";
import type { UserObj } from "../types";
import { show } from "../trace";
import { type Ctx } from "./common";

export function ObjectView({ ctx, scene }: { ctx: Ctx; scene: Scene }) {
  const o = scene.obj as UserObj;
  const changed = new Set(ctx.step.ops.filter((op) => op.oid === scene.oid && op.k === "field").map((op) => op.f));
  return (
    <div className="objcard">
      <div className="objcls">{o.cls}</div>
      {Object.entries(o.fields).map(([k, v]) => (
        <div key={k} className={`objrow ${changed.has(k) ? "hot" : ""}`}>
          <span className="objkey">.{k}</span>
          <span className="objval">{show(v, ctx.heap)}</span>
        </div>
      ))}
      {Object.keys(o.fields).length === 0 && <div className="muted">no fields</div>}
    </div>
  );
}
