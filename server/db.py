"""Local SQLite store for progress, drafts, active time and run history.

Lives outside the repo (default ~/.whydidbreak/progress.db, or $WDIB_DATA_DIR) so that
rebuilding the UI, `git clean` or a fresh clone never loses it.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

_lock = threading.Lock()
_ready: set[str] = set()

# Ordered migrations: index + 1 is the schema version it produces. Never edit a shipped one; append.
MIGRATIONS = [
    """
    CREATE TABLE progress (
        problem_id       TEXT PRIMARY KEY,
        status           TEXT NOT NULL DEFAULT 'tried',
        first_opened_at  TEXT,
        solved_at        TEXT,
        active_seconds   INTEGER NOT NULL DEFAULT 0,
        seconds_to_solve INTEGER,
        runs             INTEGER NOT NULL DEFAULT 0,
        submits          INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE drafts (
        problem_id TEXT PRIMARY KEY,
        code       TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE activity (
        problem_id TEXT NOT NULL,
        day        TEXT NOT NULL,
        seconds    INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (problem_id, day)
    );
    CREATE TABLE runs (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id     TEXT NOT NULL,
        kind           TEXT NOT NULL,
        created_at     TEXT NOT NULL,
        code           TEXT NOT NULL,
        test_index     INTEGER,
        custom_input   TEXT,
        status         TEXT NOT NULL,
        passed         INTEGER,
        total          INTEGER,
        error_type     TEXT,
        category       TEXT,
        title          TEXT,
        summary        TEXT,
        line           INTEGER,
        active_seconds INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX runs_problem ON runs (problem_id, id);
    """,
    # the company-wise problem bank (see bank.py): metadata from the company lists, specs we author
    """
    CREATE TABLE bank_problems (
        id          TEXT PRIMARY KEY,
        title       TEXT NOT NULL,
        difficulty  TEXT NOT NULL,
        level       TEXT NOT NULL,
        topics      TEXT NOT NULL DEFAULT '[]',
        status      TEXT NOT NULL DEFAULT 'pending',
        skip_reason TEXT,
        last_error  TEXT,
        spec        TEXT,
        updated_at  TEXT NOT NULL
    );
    CREATE TABLE bank_companies (
        problem_id TEXT NOT NULL,
        company    TEXT NOT NULL,
        window     TEXT NOT NULL,
        frequency  REAL,
        PRIMARY KEY (problem_id, company, window)
    );
    CREATE INDEX bank_companies_company ON bank_companies (company, window);
    """,
]


def data_dir() -> Path:
    return Path(os.environ.get("WDIB_DATA_DIR") or Path.home() / ".whydidbreak")


def db_path() -> Path:
    return data_dir() / "progress.db"


def migrate(conn: sqlite3.Connection) -> int:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for i in range(version, len(MIGRATIONS)):
        with conn:
            conn.executescript("BEGIN;" + MIGRATIONS[i] + f"; PRAGMA user_version = {i + 1};")
    return len(MIGRATIONS)


@contextmanager
def connect():
    """One connection per request; the schema is brought up to date on first use of each file."""
    path = db_path()
    key = str(path)
    if key not in _ready:
        with _lock:
            if key not in _ready:
                path.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(path)
                try:
                    conn.execute("PRAGMA journal_mode=WAL")
                    migrate(conn)
                finally:
                    conn.close()
                _ready.add(key)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:  # commit on success, roll back on error
            yield conn
    finally:
        conn.close()
