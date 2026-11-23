# Authoring problems for the company bank

`python -m server.bank next` writes batches of problems to author to `~/.whydidbreak/bank/todo-NNNN.json`. Each entry has the LeetCode `id` (slug), `title`, `difficulty` and `topics`, and may also have `previous_attempt_failed` (fix that issue this time).

Write the specs to `~/.whydidbreak/bank/out-NNNN.json` as a JSON **list** with one object per problem. Then validate and store them:

```
cd <repo> && .venv/bin/python -m server.bank import ~/.whydidbreak/bank/out-NNNN.json
```

The import prints `ready` / `skipped` / `failed` counts and an error for each failure. Fix the failures and import the same file again; importing again is safe. You're done when nothing fails.

## Content rules (important)

- **Write everything in your own words.** Don't reproduce LeetCode's statement, examples, constraints or test data, even if you remember them. Describe the same underlying task plainly, with your own example values.
- Write for someone learning. Explain the task clearly, define the edge cases (empty input, ties, which answer to return when several fit) and keep the tone friendly. Markdown is fine: `` `code` ``, **bold**, lists.
- The reference solution should be clear, idiomatic Python at the expected complexity, without being clever for its own sake. Students can read it on the Solution tab.

## Spec fields

```json
{
  "id": "plus-one",                     // the slug from the todo file, unchanged
  "fn": "plus_one",                     // snake_case function name the student writes
  "params": ["digits"],                 // parameter names, snake_case
  "statement": "…markdown…",
  "solution": "def plus_one(digits):\n    …\n",
  "tests": [ [[1, 2, 3]], [[9]], … ],   // aim for 8–12 (6 is the hard minimum); ONE value PER PARAMETER
  "visible": 3,                         // the first N tests are shown as examples (default 3)
  "explain": ["why example 1's answer is what it is", "…"],   // optional, one per visible test
  "constraints": ["`1 <= len(digits) <= 100`"],
  "hints": ["first nudge", "second, more specific nudge"],   // 2–3, never the full answer
  "compare": "exact",                   // exact | unordered | unordered2 | float
  "output": "return",                   // return | arg0 (the function changes its first argument in place)
  "kinds": {"head": "linked"},          // only for params that are a ListNode / TreeNode
  "ret": "linked",                      // only if it RETURNS a ListNode ("linked") or TreeNode ("tree")
  "returns": "Return the new head."     // optional: the wording after "# Write your solution here."
}
```

To skip a problem that doesn't fit, use `{"id": "...", "skip": "short reason"}`.

### How tests work

- The expected answers are **computed by running your `solution`**, so you never write expected outputs. The tests just have to be valid inputs, and the solution has to be correct.
- Each test is `[arg1, arg2, …]` in `params` order. A single list parameter therefore looks like `[[1, 2, 3]]`.
- Values must be JSON: numbers, strings, booleans, `null`, lists and objects. No tuples or sets.
- The first `visible` tests should be small, illustrative examples. The rest cover edge cases: empty or minimal input, duplicates, negatives, all-equal values, already-sorted and reverse-sorted input, the largest answer, and so on.
- **Keep inputs small** (lists of about 20 items or fewer, grids of about 6×6 or smaller). Every test is traced line by line for the visualizer, so a big input produces a huge trace. Each case must finish in under 2 seconds.
- Inputs must satisfy your own constraints, and no two tests may be identical.

### Linked lists and trees

- These exist already (don't define them): `ListNode(val, next)` and `TreeNode(val, left, right)`.
- A linked-list param is written as a plain list, `[1, 2, 3]`, and needs `"kinds": {"head": "linked"}`.
- A tree param uses level-order with `null` for gaps, `[3, 9, 20, null, null, 15, 7]`, and needs `"kinds": {"root": "tree"}`.
- If the function returns a node, set `"ret": "linked"` or `"ret": "tree"`. The answer is then compared as a list.
- Only a parameter that is **one** list or tree can use `kinds`. A list of linked lists or trees (merge k lists, for example) isn't supported, so take plain Python lists instead and say so in the statement.
- Cycles, random pointers and parent pointers can't be expressed this way, so skip those problems.

### Imports

Standard-library imports are fine in solutions: `heapq`, `collections`, `bisect`, `math`, `functools` and `itertools`.

### Comparing answers

- `exact` is the default, and `True` is not `1`.
- `unordered`: the answer is a list whose order doesn't matter.
- `unordered2`: a list of lists where neither the outer nor the inner order matters (subsets, groups).
- `float`: a number compared within 1e-6.
- If several answers are valid and none of these modes covers it ("return any valid index"), **make the answer unique in the statement**. For example: "return the smallest such index", or "return the pair sorted ascending". If that isn't possible, skip the problem.
- In-place problems ("modify the array, return nothing") use `"output": "arg0"`, and the judge compares the first argument after the call. With `arg0`, **any return value is ignored**. This works for a linked-list or tree first parameter too: it's compared as a list after the call. "Modify in place and return the new length" therefore becomes "modify in place and trim the list to the new length".
- The import prints a `preview` of each problem's visible examples with the answers the solution actually gives. Check them against your `explain` text.

### Adapting instead of skipping

Many problems can be rephrased as a pure function. Prefer adapting over skipping:

- **"Guess" or "isBadVersion" style API problems:** pass what the API would reveal as a parameter (for example, `first_bad(n, bad)` with the rule "versions >= bad are bad"). The statement should still ask for few checks.
- **Graph-node problems:** pass an adjacency list.
- **Design or class problems:** usually skip. Skip when the operations are the whole point (LRU cache, iterators, `Codec`). Simple ones may become a function that takes a list of operations and returns the list of results, but only if it reads naturally.
- **Skip when you don't know the problem.** If you aren't confident what the task behind a title actually asks (common for newer contest problems), skip it with `"skip": "unsure of the problem"`. Don't invent a different problem under that title: students practise these because a company asked that exact one.
- **Skip outright:** randomness, threads, SQL or shell, N-ary or graph `Node` classes, `NestedInteger` and other custom APIs, problems whose answer can't be pinned down, and anything that needs huge inputs to be meaningful.
