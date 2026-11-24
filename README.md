# WhyDidItBreak

A local Python DSA practice studio that traces code step-by-step, explains failures, and visualizes data structures and algorithms.

## Run

```bash
make setup
make start
```

Open http://localhost:8000.

For development with hot reload:

```bash
./dev.sh
```

Open http://localhost:5173.

## Features

- Python editor with line and execution tracing
- Run, submit, custom test, and playground modes
- Crash explanations and wrong-answer diffs
- Animated arrays, grids, graphs, linked lists, trees, stacks, heaps, and call trees
- Timeline playback and clickable execution history
- Worked lessons and reference solutions
- Saved drafts, progress, active-time tracking, and mistake summaries
- Company-tagged and LeetCode-style problems

## Test

```bash
make test
```

## Storage and security

Progress and drafts are stored locally in `~/.whydidbreak/progress.db`. Set `WDIB_DATA_DIR` to use another directory.

Code runs locally with the server user's permissions. The server only binds to `127.0.0.1`.
