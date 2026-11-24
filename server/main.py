"""FastAPI app: trace endpoint, lessons, and the built frontend."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import bank, history, judge, lessons, problems, tracer

@asynccontextmanager
async def _lifespan(_app):
    # the authored company problems ship in the repo; bring a fresh or older database up to date
    try:
        bank.load_seed()
    except Exception as e:  # never keep the app from starting over it
        print(f"bank seed not loaded: {e}")
    yield


app = FastAPI(title="WhyDidItBreak", lifespan=_lifespan)
app.add_middleware(GZipMiddleware, minimum_size=2000)

DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")


class RunRequest(BaseModel):
    code: str
    stdin: str = ""
    problem_id: str | None = None
    test: int | None = None  # index into the problem's tests
    custom: str | None = None  # or a custom input, one argument per line
    watch: str | None = None  # "sample" | "buggy" | "solution": reference code, recorded as watched
    watch_problem: str | None = None  # the problem a watched sample belongs to (samples run unjudged)


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
        res = tracer.run(req.code, req.stdin)
        if req.watch and req.watch != "replay" and req.watch_problem:
            history.record_run(req.watch_problem, "watch", req.code,
                               {"status": "pass", "title": f"Watched the {req.watch} code"})
        return res
    problem = _problem(req.problem_id)
    try:
        args = judge.cases_of(problem, req.test, req.custom)
        res = judge.trace(req.code, problem, args)
    except ValueError as e:  # unreadable or ill-typed custom input
        raise HTTPException(400, str(e)) from None
    if req.watch == "replay":  # re-tracing an old run from the history isn't a new attempt
        pass
    elif req.watch:
        history.record_run(problem["id"], "watch", req.code, {"status": "pass", "title": f"Watched the {req.watch}"},
                           req.test, req.custom)
    else:
        res["run_id"] = history.record_run(problem["id"], "run", req.code, history.describe_trace(res),
                                           None if req.custom is not None else req.test, req.custom)
    return res


@app.post("/api/submit")
def submit(req: SubmitRequest):
    if len(req.code) > 50_000:
        raise HTTPException(413, "Code too long")
    res = judge.submit(req.code, _problem(req.problem_id))
    res["run_id"] = history.record_run(req.problem_id, "submit", req.code, history.describe_submit(res))
    return res


# ---------------------------------------------------------------- progress, drafts, history

class Activity(BaseModel):
    problem_id: str
    seconds: float


class Draft(BaseModel):
    code: str


class ImportRequest(BaseModel):
    progress: dict[str, str] = {}
    drafts: dict[str, str] = {}


@app.get("/api/progress")
def get_progress():
    return history.progress()


@app.post("/api/progress/{problem_id}/open")
def opened(problem_id: str):
    history.open_problem(problem_id)
    return {"ok": True}


@app.delete("/api/progress")
def reset_all(drafts: bool = False):
    return history.reset(None, drafts)


@app.delete("/api/progress/{problem_id}")
def reset_one(problem_id: str, drafts: bool = False):
    _problem(problem_id)
    return history.reset(problem_id, drafts)


@app.post("/api/activity")
def activity(req: Activity):
    history.add_activity(req.problem_id, req.seconds)
    return {"ok": True}


@app.get("/api/drafts/{problem_id}")
def get_draft(problem_id: str):
    return {"code": history.get_draft(problem_id)}


@app.put("/api/drafts/{problem_id}")
def put_draft(problem_id: str, req: Draft):
    if len(req.code) > 50_000:
        raise HTTPException(413, "Code too long")
    _problem(problem_id)
    history.save_draft(problem_id, req.code)
    return {"ok": True}


@app.post("/api/import")
def import_local(req: ImportRequest):
    return history.import_local(req.progress, req.drafts)


@app.get("/api/learnings")
def learnings():
    return history.learnings()


@app.get("/api/runs/{run_id}")
def get_run(run_id: int):
    run = history.get_run(run_id)
    if not run:
        raise HTTPException(404, "No such run")
    return run


@app.get("/api/problems")
def list_problems():
    # company names are sent once and referenced by index: the bank has thousands of problems
    rows = problems.catalog()
    names = sorted({c for r in rows for c in r["companies"]}, key=str.lower)
    index = {c: i for i, c in enumerate(names)}
    for r in rows:
        r["companies"] = [index[c] for c in r["companies"]]
    return {"levels": problems.LEVELS, "companies": names, "problems": rows}


@app.get("/api/problems/{problem_id}")
def get_problem(problem_id: str):
    problem = _problem(problem_id)
    out = judge.detail(problem, lessons.by_id(problem["topic"]) if problem["topic"] else None)
    lc = problem.get("lc") or (problem["id"] if problem.get("bank") else None)
    out["companies"] = bank.company_tags().get(lc, []) if lc else []
    return out


@app.get("/api/companies")
def list_companies():
    return {"source": bank.SOURCE_NAME, "companies": bank.companies()}


@app.get("/api/companies/{company}")
def company(company: str, window: str = "all"):
    """{problem id: how often this company asks it} for one time window."""
    freq = bank.company_frequency(company, window)
    to_local = {p["lc"]: p["id"] for p in problems.PROBLEMS if p.get("lc")}
    return {"company": company, "window": window,
            "frequency": {to_local.get(slug, slug): f for slug, f in freq.items()}}


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
