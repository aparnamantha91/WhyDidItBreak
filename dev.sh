#!/usr/bin/env bash
# Dev mode: FastAPI (auto-reload) on :8000 + Vite (hot reload) on :5173.
# Open http://localhost:5173
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
[ -d web/node_modules ] || (cd web && npm install)
trap 'kill 0' EXIT
.venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir server &
(cd web && npx vite --host 127.0.0.1) &
wait
