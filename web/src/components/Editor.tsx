import { useEffect, useRef } from "react";
import MonacoEditor, { loader, type OnMount } from "@monaco-editor/react";
import * as monaco from "monaco-editor/editor/editor.api";
import "monaco-editor/languages/definitions/python/register";
import editorWorker from "monaco-editor/editor/editor.worker?worker";
import { useStore } from "../store";

// bundle Monaco locally (no CDN) so the app works fully offline on localhost
self.MonacoEnvironment = { getWorker: () => new editorWorker() };
loader.config({ monaco });

type Ed = monaco.editor.IStandaloneCodeEditor;

export function Editor() {
  const own = useStore((s) => s.code);
  const viewing = useStore((s) => s.viewing);
  const stopWatching = useStore((s) => s.stopWatching);
  const code = viewing ? viewing.code : own;
  const setCode = useStore((s) => s.setCode);
  const res = useStore((s) => s.res);
  const i = useStore((s) => s.step);
  const dirty = useStore((s) => s.dirty);
  const hoverLine = useStore((s) => s.hoverLine);
  const edRef = useRef<Ed | null>(null);
  const decos = useRef<monaco.editor.IEditorDecorationsCollection | null>(null);

  const onMount: OnMount = (ed, m) => {
    edRef.current = ed;
    decos.current = ed.createDecorationsCollection();
    m.editor.defineTheme("wdib", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment", foreground: "64748b", fontStyle: "italic" },
        { token: "keyword", foreground: "c084fc" },
        { token: "number", foreground: "fbbf24" },
        { token: "string", foreground: "86efac" },
      ],
      colors: {
        "editor.background": "#0b1020",
        "editorGutter.background": "#0b1020",
        "editor.lineHighlightBackground": "#00000000",
        "editor.lineHighlightBorder": "#00000000",
        "editorLineNumber.foreground": "#334155",
        "editorLineNumber.activeForeground": "#94a3b8",
      },
    });
    m.editor.setTheme("wdib");
    ed.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.Enter, () => useStore.getState().run());
  };

  // trace decorations
  useEffect(() => {
    const ed = edRef.current;
    if (!ed || !decos.current) return;
    const model = ed.getModel();
    if (!model) return;
    const list: monaco.editor.IModelDeltaDecoration[] = [];
    const markers: monaco.editor.IMarkerData[] = [];
    const err = res?.error;
    if (res && !dirty) {
      const step = res.steps[i];
      if (step) {
        // hit counts up to this step
        const hits = new Map<number, number>();
        for (let k = 0; k <= i; k++) {
          const s = res.steps[k];
          if (s.ev === "line") hits.set(s.line, (hits.get(s.line) ?? 0) + 1);
        }
        for (const [ln, c] of hits) {
          if (ln < 1 || ln > model.getLineCount()) continue;
          list.push({
            range: new monaco.Range(ln, model.getLineMaxColumn(ln), ln, model.getLineMaxColumn(ln)),
            options: { after: { content: `  ×${c}`, inlineClassName: "hitcount" } },
          });
        }
        const prev = i > 0 ? res.steps[i - 1] : null;
        if (prev && prev.line !== step.line && prev.line >= 1) {
          list.push({ range: new monaco.Range(prev.line, 1, prev.line, 1), options: { isWholeLine: true, className: "line-prev" } });
        }
        const atErr = err?.step === i;
        if (step.line >= 1) {
          list.push({
            range: new monaco.Range(step.line, 1, step.line, 1),
            options: {
              isWholeLine: true,
              className: atErr ? "line-error" : step.ev === "return" ? "line-return" : "line-current",
              glyphMarginClassName: atErr ? "glyph-error" : "glyph-current",
            },
          });
          // keep the active line visible while stepping
          ed.revealLineInCenterIfOutsideViewport(step.line, monaco.editor.ScrollType.Smooth);
        }
        // frames below the top: show where each caller is waiting
        for (const f of (res.pool[step.frames] as number[]).slice(0, -1)) {
          const fr = res.pool[f] as { line: number };
          if (fr.line >= 1 && fr.line !== step.line)
            list.push({ range: new monaco.Range(fr.line, 1, fr.line, 1), options: { isWholeLine: true, className: "line-caller" } });
        }
      }
      const why = res.verdict?.why;
      if (why?.line && why.line <= model.getLineCount()) {
        list.push({
          range: new monaco.Range(why.line, 1, why.line, 1),
          options: {
            isWholeLine: true,
            className: "line-suspect",
            glyphMarginClassName: "glyph-suspect",
            glyphMarginHoverMessage: { value: "Where the wrong answer comes from" },
          },
        });
      }
      if (err?.line && err.line <= model.getLineCount()) {
        list.push({ range: new monaco.Range(err.line, 1, err.line, 1), options: { glyphMarginClassName: "glyph-error" } });
      }
      if (hoverLine && hoverLine <= model.getLineCount()) {
        list.push({ range: new monaco.Range(hoverLine, 1, hoverLine, 1), options: { isWholeLine: true, className: "line-culprit" } });
      }
    }
    if (err && (!dirty || !res?.steps.length)) {
      const span = err.span ?? (err.line ? [err.line, 1, err.line, model.getLineMaxColumn(Math.min(err.line, model.getLineCount()))] : null);
      if (span && span[0] <= model.getLineCount()) {
        markers.push({
          severity: monaco.MarkerSeverity.Error,
          message: `${err.title ?? err.type}: ${err.why ?? err.msg}`,
          startLineNumber: span[0],
          startColumn: span[1],
          endLineNumber: span[2],
          endColumn: Math.max(span[3], span[1] + 1),
        });
      }
    }
    decos.current.set(list);
    monaco.editor.setModelMarkers(model, "wdib", markers);
  }, [res, i, dirty, hoverLine]);

  return (
    <div className={`editor ${viewing ? "watching" : ""}`}>
      {viewing && (
        <div className="watch-bar">
          <span>👁 {viewing.label} (read-only)</span>
          <button onClick={stopWatching}>← Back to my code</button>
        </div>
      )}
      <MonacoEditor
        language="python"
        value={code}
        onChange={(v) => setCode(v ?? "")}
        onMount={onMount}
        options={{
          readOnly: !!viewing,
          fontSize: 14,
          fontFamily: "'JetBrains Mono', 'Fira Code', ui-monospace, Menlo, monospace",
          fontLigatures: true,
          minimap: { enabled: false },
          glyphMargin: true,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 4,
          padding: { top: 12 },
          renderLineHighlight: "none",
          smoothScrolling: true,
          cursorBlinking: "smooth",
        }}
      />
    </div>
  );
}
