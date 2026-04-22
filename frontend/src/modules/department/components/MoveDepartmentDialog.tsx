import type { DepartmentNode } from "../types";

export function MoveDepartmentDialog(_props: {
  source: DepartmentNode;
  tree: DepartmentNode[];
  onClose: () => void;
  onMoved: () => void | Promise<void>;
}) {
  return null;
}
