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

- **43 LeetCode-style problems**, Beginner to Advanced (arrays, two pointers, sliding window, stacks, hash maps, linked lists, trees, heaps, graphs, DP, backtracking). Each has a statement, examples, hints you reveal one at a time, and a starter function. Your draft is saved per problem, and solved problems get a ✓.
- **Run** traces your function on one test (an example, any test from the last submit, or your own input). **Submit** checks every test and takes you straight to the first one that breaks.
- **Why it broke**:
  - *Crash*: off-by-one indexes (drawn as a ghost slot past the end), `None` pointers, missing keys, runaway recursion (with the argument trend), empty pops, typos (with "did you mean"), syntax errors and divide-by-zero. Each comes with the culprit variable's value history; click a value to jump to the step that set it.
  - *Too slow*: infinite loops, with the variables that never change or that cycle.
  - *Wrong answer*: input, expected and returned values side by side, the first position where they differ, and a jump to the step where your function returned so you can walk backwards from it.
- **Sample code to look up**: every problem links to a worked example of its technique (working, and with a typical bug) and to a reference solution hidden behind a reveal. Watching either one run never touches your own code.
- **Monaco Python editor**: highlights the current line, the callers' lines and the crash line, and shows how many times each line has run (`×12`). Run with `Ctrl/⌘+Enter`.
- **Timeline**: scrub through the run. It plots call depth and marks swaps, calls, the return and the crash. Keys: `←/→` step (`Shift` jumps 10), `Space` play, `Home/End`. Playback speed goes from 0.1× to 10×.
- **Auto-detected visualizations** (you can override them per variable):
  - number lists as animated bars, with index pointers (`i`, `j`, `lo`, `mid`, …), compare glow and swap arcs
  - 2D lists as heatmap grids (DP tables)
  - dicts as hash rows and sets as chips
  - stacks, queues/deques and `heapq` heaps (tree plus array)
  - adjacency dicts as force-laid graphs, with visited, frontier, current-node and distance labels
  - `.next` objects as linked lists, with pointer variables riding the nodes
  - `.left/.right/.children` objects as trees
  - recursion as a live call tree
- **Narration log and cost counters**: a running log of what each line did ("Swapped a[1] ↔ a[2]"), with the current step large at the bottom and earlier steps clickable, plus totals of comparisons, swaps, writes and calls.
- **Playground**: run any Python, with no problem attached.
- **Progress database**: every Run and Submit is recorded with what went wrong, along with your *active* time on each problem (only while the tab is focused and you've interacted in the last minute) and the active time it took to solve. Drafts are saved there too. It's a SQLite file at `~/.whydidbreak/progress.db` (set `WDIB_DATA_DIR` to move it), outside the repo, so rebuilds and fresh clones keep it. Reset one problem from its header, or everything from the Learnings page.
- **📈 Learnings page**: solved count, active time, median time to solve, streak and a 30-day activity chart; your recurring mistakes grouped by kind (off-by-one, `None` pointers, missing return, …) with the rule to remember; a journal per problem with the diff that fixed it; and a filterable run log where any old run can be replayed in the visual debugger or restored into the editor. Export it all as Markdown.

## How it works

- `server/runner.py` runs your code in a separate Python process under `sys.settrace`. It snapshots every frame and every reachable object at each step, and records which indexes each line is about to read. Limits are 3000 steps and 4 seconds.
- `server/narrate.py` diffs consecutive snapshots into operations and narration. `server/explain.py` turns the exception into the error card. `server/tracer.py` deduplicates the trace.
- `server/problems.py` holds the problems; `server/judge.py` wraps your function in a hidden test harness (so `ListNode`/`TreeNode` exist and line numbers stay yours), runs all tests untraced in `server/judge_runner.py`, and takes the expected answers from the reference solutions. `server/lessons.py` is the sample code.
- `server/db.py` is the SQLite store (schema migrations via `PRAGMA user_version`); `server/history.py` records runs, categorises mistakes and builds the Learnings view.
- `web/` is React, Vite, Monaco, D3 and Framer Motion. `src/detect.ts` decides how to draw each variable, and `src/viz/*` holds the renderers.

> Code runs on your own machine with your user's permissions; the server binds to 127.0.0.1 only.
