export type DiffLine = { t: "same" | "add" | "del"; text: string };

/** Line diff via longest common subsequence (inputs here are small: one solution each). */
export function diffLines(a: string, b: string): DiffLine[] {
  const x = a.replace(/\s+$/, "").split("\n");
  const y = b.replace(/\s+$/, "").split("\n");
  const n = x.length;
  const m = y.length;
  const L: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--) L[i][j] = x[i] === y[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (x[i] === y[j]) {
      out.push({ t: "same", text: x[i] });
      i++;
      j++;
    } else if (L[i + 1][j] >= L[i][j + 1]) out.push({ t: "del", text: x[i++] });
    else out.push({ t: "add", text: y[j++] });
  }
  while (i < n) out.push({ t: "del", text: x[i++] });
  while (j < m) out.push({ t: "add", text: y[j++] });
  return out;
}

/** Only the changed lines plus `ctx` lines of context around them. */
export function hunks(lines: DiffLine[], ctx = 2): (DiffLine | null)[] {
  const keep = lines.map(() => false);
  lines.forEach((l, k) => {
    if (l.t !== "same") for (let d = -ctx; d <= ctx; d++) if (lines[k + d]) keep[k + d] = true;
  });
  const out: (DiffLine | null)[] = [];
  lines.forEach((l, k) => {
    if (keep[k]) out.push(l);
    else if (out.length && out[out.length - 1] !== null) out.push(null); // a gap
  });
  if (out[out.length - 1] === null) out.pop();
  return out;
}
