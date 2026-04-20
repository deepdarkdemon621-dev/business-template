export type Scope = "global" | "dept_tree" | "dept" | "own";

const PRIORITY: Record<Scope, number> = {
  global: 3,
  dept_tree: 2,
  dept: 1,
  own: 0,
};

export function widest(a: Scope, b: Scope): Scope {
  return PRIORITY[a] >= PRIORITY[b] ? a : b;
}

export function atLeast(actual: Scope, required: Scope): boolean {
  return PRIORITY[actual] >= PRIORITY[required];
}
