"""FastAPI app: trace endpoint, lessons, and the built frontend."""
from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import judge, lessons, problems, tracer

app = FastAPI(title="WhyDidItBreak")
app.add_middleware(GZipMiddleware, minimum_size=2000)

DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")


class RunRequest(BaseModel):
    code: str
    stdin: str = ""
    problem_id: str | None = None
    test: int | None = None  # index into the problem's tests
    custom: str | None = None  # or a custom input, one argument per line


class SubmitRequest(BaseModel):
    code: str
    problem_id: str


def _problem(problem_id: str) -> dict:
    problem = problems.by_id(problem_id)
    if not problem:
        raise HTTPException(404, "No such problem")
    return problem


@app.post("/api/run")
def run(req: RunRequest):
    if len(req.code) > 50_000:
        raise HTTPException(413, "Code too long")
    if not req.problem_id:
        return tracer.run(req.code, req.stdin)
    problem = _problem(req.problem_id)
    try:
        args = judge.cases_of(problem, req.test, req.custom)
        return judge.trace(req.code, problem, args)
    except ValueError as e:  # unreadable or ill-typed custom input
        raise HTTPException(400, str(e)) from None


@app.post("/api/submit")
def submit(req: SubmitRequest):
    if len(req.code) > 50_000:
        raise HTTPException(413, "Code too long")
    return judge.submit(req.code, _problem(req.problem_id))


@app.get("/api/problems")
def list_problems():
    return {"levels": problems.LEVELS, "problems": [judge.info(p) for p in problems.PROBLEMS]}


@app.get("/api/problems/{problem_id}")
def get_problem(problem_id: str):
    problem = _problem(problem_id)
    return judge.detail(problem, lessons.by_id(problem["topic"]))


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
