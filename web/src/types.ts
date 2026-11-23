export type Val =
  | { t: "none" }
  | { t: "bool"; v: boolean }
  | { t: "int"; v: number | string; big?: boolean }
  | { t: "float"; v: number | string; special?: boolean }
  | { t: "str"; v: string; cut?: boolean }
  | { t: "func"; v: string }
  | { t: "repr"; v: string; cls?: string }
  | { t: "ref"; r: string };

export type SeqObj = { t: "list" | "tuple" | "deque" | "set"; items: Val[]; more?: number };
export type DictObj = { t: "dict"; entries: [Val, Val][]; more?: number; default?: boolean };
export type UserObj = { t: "obj"; cls: string; fields: Record<string, Val> };
export type HeapObj = SeqObj | DictObj | UserObj;
export type Heap = Record<string, HeapObj>;

export interface Frame {
  fn: string;
  fid: string;
  line: number;
  vars: Record<string, Val>;
}

export interface Op {
  k: string;
  var: string;
  oid?: string;
  i?: number;
  j?: number;
  v?: string;
  old?: string | null;
  key?: string;
  f?: string;
  role?: string;
  fid?: string;
  new?: boolean;
}

export interface Access {
  var: string;
  idx: Val[];
  expr: string[];
  text: string;
  cmp: boolean;
  ok?: boolean;
}

export interface Counters {
  steps: number;
  cmp: number;
  swaps: number;
  writes: number;
  calls: number;
}

export interface Step {
  ev: "line" | "call" | "return" | "exception";
  line: number;
  fn: string;
  fid: string;
  frames: number; // pool index
  heap: number; // pool index
  out: number;
  acc?: Access[];
  ret?: Val;
  exc?: { type: string; msg: string };
  ops: Op[];
  did: string[];
  next: string | null;
  cnt: Counters;
}

export interface Culprit {
  name: string;
  value: string;
  type: string;
  history: { step: number; line: number; v: string }[];
  changed_step?: number;
  changed_line?: number;
  note?: string;
}

export interface ErrorInfo {
  type: string;
  msg: string;
  line?: number;
  step?: number;
  title?: string;
  why?: string;
  hint?: string;
  code?: string;
  span?: [number, number, number, number];
  culprits: Culprit[];
  viz?: {
    kind: "oob" | "missing_key" | "none" | "recursion" | "loop" | "empty";
    var?: string;
    idx?: number;
    len?: number;
    expr?: string;
    depth?: number;
    path?: number[];
    key?: string;
    attr?: string;
    fn?: string;
    calls?: string[];
    frozen?: string[];
    runs?: number;
    line?: number;
  };
}

export interface Meta {
  index_vars?: Record<string, string[]>;
  roles?: Record<string, string>;
  funcs?: string[];
  recursive?: string[];
  compare_lines?: number[];
  loops?: { line: number; end: number; kind: string; names: string[]; cond: string }[];
}

export interface Verdict {
  status: "pass" | "wrong" | "error" | "timeout";
  input: string;
  expected?: string;
  got?: string;
  diff?: string;
  note?: string;
  stdout?: string;
  error?: { type: string; msg: string; line: number | null };
  why?: WrongWhy;
}

/** Wrong-answer forensics: where the returned value went wrong. */
export interface WrongWhy {
  kind: "never_written" | "wrong_write" | "too_short" | "too_long" | "no_return" | "wrong_value";
  summary: string;
  detail: string[];
  hint?: string;
  line?: number | null;
  jumps: { label: string; step: number; line?: number }[];
  culprits: Culprit[];
  var?: string;
  oid?: string;
  index?: number;
  expected_item?: string;
  got_item?: string;
}

export interface RunResult {
  steps: Step[];
  pool: unknown[];
  stdout: string;
  error: ErrorInfo | null;
  meta: Meta;
  verdict?: Verdict; // problem mode: how this test case went
  return_step?: number;
  truncated?: boolean;
}

export interface ProblemInfo {
  id: string;
  title: string;
  level: string;
  topic: string;
}

export interface ProblemCase {
  index: number;
  input: string;
  expected: string;
  explain: string | null;
}

export interface Problem extends ProblemInfo {
  statement: string;
  constraints: string[];
  hints: string[];
  fn: string;
  params: string[];
  starter: string;
  solution: string;
  cases: ProblemCase[];
  total: number;
  lesson: { id: string; title: string; concept: string; code: string; buggy: string } | null;
}

export interface SubmitRow extends Omit<Verdict, "status"> {
  index: number;
  status: Verdict["status"] | "skipped";
}

export interface SubmitResult {
  results: SubmitRow[];
  passed: number;
  total: number;
  fatal?: { type: string; title?: string; why?: string; hint?: string; msg: string };
}

export interface Snapshot {
  frames: Frame[];
  heap: Heap;
}
