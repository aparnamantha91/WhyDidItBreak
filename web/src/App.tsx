import { useEffect } from "react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { useStore } from "./store";
import { Toolbar } from "./components/Toolbar";
import { Timeline } from "./components/Timeline";
import { Editor } from "./components/Editor";
import { Console } from "./components/Console";
import { Visualizer } from "./components/Visualizer";
import { Inspector } from "./components/Inspector";
import { Problems } from "./components/Problems";
import { Learnings } from "./components/Learnings";
import { startActivityTracking } from "./activity";

export default function App() {
  const showPanel = useStore((s) => s.showPanel);
  const playing = useStore((s) => s.playing);
  const speed = useStore((s) => s.speed);

  const view = useStore((s) => s.view);
  useEffect(() => {
    useStore.getState().init();
    startActivityTracking();
    const onHash = () => useStore.setState({ view: location.hash === "#/learnings" ? "learnings" : "studio" });
    window.addEventListener("popstate", onHash);
    window.addEventListener("hashchange", onHash);
    return () => {
      window.removeEventListener("popstate", onHash);
      window.removeEventListener("hashchange", onHash);
    };
  }, []);

  // playback loop
  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => {
      const { step, res, error } = { ...useStore.getState(), error: useStore.getState().res?.error };
      const n = res?.steps.length ?? 0;
      if (step >= n - 1 || (error?.step !== undefined && step >= error.step)) {
        useStore.setState({ playing: false });
        return;
      }
      useStore.getState().setStep(step + 1);
    }, speed);
    return () => clearInterval(t);
  }, [playing, speed]);

  // keyboard: arrows / space / home / end (not while typing in the editor)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target instanceof HTMLElement ? e.target : null;
      if (t && (t.closest(".monaco-editor") || ["INPUT", "SELECT", "TEXTAREA"].includes(t.tagName))) return;
      if (useStore.getState().view !== "studio") return;
      const s = useStore.getState();
      if (e.key === "ArrowRight") s.stepBy(e.shiftKey ? 10 : 1);
      else if (e.key === "ArrowLeft") s.stepBy(e.shiftKey ? -10 : -1);
      else if (e.key === " ") s.togglePlay();
      else if (e.key === "Home") s.setStep(0);
      else if (e.key === "End") s.setStep(Number.MAX_SAFE_INTEGER);
      else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) s.run();
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="app">
      <Toolbar />
      {view === "learnings" ? (
        <Learnings />
      ) : (
      <>
      <Timeline />
      <Group orientation="horizontal" className="main">
        {showPanel && (
          <>
            <Panel id="problems" defaultSize="24%" minSize={220} maxSize="40%">
              <Problems />
            </Panel>
            <Separator className="sep-v" />
          </>
        )}
        <Panel id="code" defaultSize={showPanel ? "34%" : "45%"} minSize={280}>
          <Group orientation="vertical">
            <Panel id="editor" defaultSize="64%" minSize={120}>
              <Editor />
            </Panel>
            <Separator className="sep-h" />
            <Panel id="console" defaultSize="36%" minSize={90}>
              <Console />
            </Panel>
          </Group>
        </Panel>
        <Separator className="sep-v" />
        <Panel id="viz" minSize={340}>
          <Group orientation="vertical">
            <Panel id="canvas" defaultSize="72%" minSize={160}>
              <Visualizer />
            </Panel>
            <Separator className="sep-h" />
            <Panel id="inspector" defaultSize="28%" minSize={90}>
              <Inspector />
            </Panel>
          </Group>
        </Panel>
      </Group>
      </>
      )}
    </div>
  );
}
