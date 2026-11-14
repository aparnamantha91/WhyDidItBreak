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

export interface RunResult {
  steps: Step[];
  pool: unknown[];
  stdout: string;
  error: ErrorInfo | null;
  meta: Meta;
}

export interface LessonInfo {
  id: string;
  level: string;
  title: string;
  concept: string;
}

export interface Lesson extends LessonInfo {
  code: string;
  buggy: string;
  expected: string | null;
}

export interface Snapshot {
  frames: Frame[];
  heap: Heap;
}
