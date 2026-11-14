# WhyDidItBreak

A localhost DSA learning studio: write Python on the left, and watch every step of it run on the right. When the code is wrong, it shows **where it broke, which value caused it, and how that value got there**.

## Run it

```bash
make setup      # once: Python venv + npm install
make start      # build the UI and serve everything at http://localhost:8000
```

For development with hot reload (FastAPI on :8000, Vite on :5173):

```bash
./dev.sh        # open http://localhost:5173
```

Tests: `make test`

## What you get

- **Monaco Python editor**: highlights the current line, the callers' lines and the crash line, and shows how many times each line has run (`×12`). Run with `Ctrl/⌘+Enter`.
- **Timeline**: scrub through the run. It plots call depth and marks swaps, calls and the crash. Keys: `←/→` step (`Shift` jumps 10), `Space` play, `Home/End`.
- **Auto-detected visualizations** (you can override them per variable):
  - number lists as animated bars, with index pointers (`i`, `j`, `lo`, `mid`, …), compare glow and swap arcs
  - 2D lists as heatmap grids (DP tables)
  - dicts as hash rows and sets as chips
  - stacks, queues/deques and `heapq` heaps (tree plus array)
  - adjacency dicts as force-laid graphs, with visited, frontier, current-node and distance labels
  - `.next` objects as linked lists, with pointer variables riding the nodes
  - `.left/.right/.children` objects as trees
  - recursion as a live call tree
- **Narration and cost counters**: what the last line did ("Swapped a[1] ↔ a[2]"), what's being compared next, and running totals of comparisons, swaps, writes and calls.
- **Error forensics**: off-by-one indexes (drawn as a ghost slot past the end), `None` pointers, missing keys, runaway recursion (with the argument trend), infinite loops (variables that never change, or that cycle), empty pops, typos (with "did you mean"), syntax errors and divide-by-zero. Each comes with the culprit variable's value history; click any value to jump to the step that set it.
- **23 lessons** from Beginner to Advanced. Each has a working version and a 🐞 buggy version. Logic bugs (wrong answer, no crash) are caught by comparing the output with the reference solution.

## How it works

- `server/runner.py` runs your code in a separate Python process under `sys.settrace`. It snapshots every frame and every reachable object at each step, and records which indexes each line is about to read. Limits are 3000 steps and 4 seconds.
- `server/narrate.py` diffs consecutive snapshots into operations and narration. `server/explain.py` turns the exception into the error card. `server/tracer.py` deduplicates the trace.
- `web/` is React, Vite, Monaco, D3 and Framer Motion. `src/detect.ts` decides how to draw each variable, and `src/viz/*` holds the renderers.

> Code runs on your own machine with your user's permissions; the server binds to 127.0.0.1 only.
