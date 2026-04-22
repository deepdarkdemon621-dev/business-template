import type { DepartmentNode } from "../types";

export type EditModalState =
  | { mode: "create"; parentId: string }
  | { mode: "rename"; node: DepartmentNode };

export function DepartmentEditModal(_props: {
  state: EditModalState;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  return null;
}
