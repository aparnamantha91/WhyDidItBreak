.PHONY: setup start dev test

setup:
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt
	cd web && npm install

# Build the UI once and serve everything from http://localhost:8000
start:
	cd web && npx vite build
	.venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8000

dev:
	./dev.sh

test:
	.venv/bin/python -m pytest -q server/tests
