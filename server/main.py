"""FastAPI app: trace endpoint, lessons, and the built frontend."""
from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import lessons, tracer

app = FastAPI(title="WhyDidItBreak")
app.add_middleware(GZipMiddleware, minimum_size=2000)

DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")


class RunRequest(BaseModel):
    code: str
    stdin: str = ""


@app.post("/api/run")
def run(req: RunRequest):
    if len(req.code) > 50_000:
        raise HTTPException(413, "Code too long")
    return tracer.run(req.code, req.stdin)


@lru_cache(maxsize=64)
def _expected(lesson_id: str) -> str | None:
    lesson = lessons.by_id(lesson_id)
    if not lesson:
        return None
    raw = tracer.run_raw(lesson["code"])
    return None if raw.get("error") else raw["stdout"]


@app.get("/api/lessons")
def list_lessons():
    return {
        "levels": lessons.LEVELS,
        "lessons": [{k: v for k, v in lesson.items() if k not in ("code", "buggy")}
                    for lesson in lessons.LESSONS],
    }


@app.get("/api/lessons/{lesson_id}")
def get_lesson(lesson_id: str):
    lesson = lessons.by_id(lesson_id)
    if not lesson:
        raise HTTPException(404, "No such lesson")
    return {**lesson, "expected": _expected(lesson_id)}


if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = os.path.realpath(os.path.join(DIST, path))
        if path and f.startswith(os.path.realpath(DIST) + os.sep) and os.path.isfile(f):
            return FileResponse(f)
        return FileResponse(os.path.join(DIST, "index.html"))
