import { useEffect } from "react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { useStore } from "./store";
import { Toolbar } from "./components/Toolbar";
import { Timeline } from "./components/Timeline";
import { Editor } from "./components/Editor";
import { Console } from "./components/Console";
import { Visualizer } from "./components/Visualizer";
import { Inspector } from "./components/Inspector";
import { Lessons } from "./components/Lessons";

export default function App() {
  const showLessons = useStore((s) => s.showLessons);
  const playing = useStore((s) => s.playing);
  const speed = useStore((s) => s.speed);

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
      <Timeline />
      <Group orientation="horizontal" className="main">
        {showLessons && (
          <>
            <Panel id="lessons" defaultSize="17%" minSize={180} maxSize="30%">
              <Lessons />
            </Panel>
            <Separator className="sep-v" />
          </>
        )}
        <Panel id="code" defaultSize={showLessons ? "38%" : "45%"} minSize={280}>
          <Group orientation="vertical">
            <Panel id="editor" defaultSize="74%" minSize={120}>
              <Editor />
            </Panel>
            <Separator className="sep-h" />
            <Panel id="console" defaultSize="26%" minSize={60}>
              <Console />
            </Panel>
          </Group>
        </Panel>
        <Separator className="sep-v" />
        <Panel id="viz" minSize={340}>
          <Group orientation="vertical">
            <Panel id="canvas" defaultSize="70%" minSize={160}>
              <Visualizer />
            </Panel>
            <Separator className="sep-h" />
            <Panel id="inspector" defaultSize="30%" minSize={90}>
              <Inspector />
            </Panel>
          </Group>
        </Panel>
      </Group>
    </div>
  );
}
