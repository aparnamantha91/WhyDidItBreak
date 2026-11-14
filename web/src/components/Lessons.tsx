import { useEffect } from "react";
import { useStore } from "../store";
import { md } from "./ErrorCard";

const LEVEL_ICON: Record<string, string> = { Beginner: "🌱", Intermediate: "🔥", Advanced: "🚀" };

export function Lessons() {
  const { lessons, levels, lesson, variant, fetchLessons, openLesson } = useStore();
  useEffect(() => {
    fetchLessons();
  }, [fetchLessons]);

  return (
    <div className="lessons">
      {lesson && (
        <div className="lesson-current">
          <div className="lc-level">{LEVEL_ICON[lesson.level]} {lesson.level}</div>
          <div className="lc-title">{lesson.title}</div>
          <p className="lc-concept">{md(lesson.concept)}</p>
          <div className="lc-btns">
            <button className={variant === "code" ? "on" : ""} onClick={() => openLesson(lesson.id, "code")}>✓ Working</button>
            <button className={`bug ${variant === "buggy" ? "on" : ""}`} onClick={() => openLesson(lesson.id, "buggy")}>
              🐞 Buggy
            </button>
          </div>
          {variant === "buggy" && <p className="muted small">This version has a bug. Run it, find where it breaks, then fix it!</p>}
        </div>
      )}
      {levels.map((lvl) => (
        <div key={lvl} className="level">
          <div className="level-title">
            {LEVEL_ICON[lvl]} {lvl}
          </div>
          {lessons
            .filter((l) => l.level === lvl)
            .map((l) => (
              <div key={l.id} className={`lesson-item ${lesson?.id === l.id ? "active" : ""}`}>
                <button className="li-main" onClick={() => openLesson(l.id, "code")} title={l.concept}>
                  {l.title}
                </button>
                <button className="li-bug" onClick={() => openLesson(l.id, "buggy")} title="Open the buggy version">
                  🐞
                </button>
              </div>
            ))}
        </div>
      ))}
      {!lessons.length && <div className="muted pad small">Lessons load from the Python server…</div>}
    </div>
  );
}
