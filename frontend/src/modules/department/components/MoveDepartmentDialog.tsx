import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tree } from "@/components/ui/tree";
import { problemMessage } from "@/lib/problem-details";
import { moveDepartment } from "../api";
import type { DepartmentNode } from "../types";

function flatSourceSubtreeIds(n: DepartmentNode): Set<string> {
  const out = new Set<string>([n.id]);
  for (const c of n.children) for (const id of flatSourceSubtreeIds(c)) out.add(id);
  return out;
}

export function MoveDepartmentDialog(props: {
  source: DepartmentNode;
  tree: DepartmentNode[];
  onClose: () => void;
  onMoved: () => void | Promise<void>;
}) {
  const { source, tree, onClose, onMoved } = props;
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [targetId, setTargetId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Disallow picking the source or any of its descendants as the new parent.
  const blocked = flatSourceSubtreeIds(source);

  async function onSubmit() {
    if (!targetId) return;
    setSubmitting(true);
    setError(null);
    try {
      await moveDepartment(source.id, { newParentId: targetId });
      await onMoved();
    } catch (err) {
      setError(problemMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="flex w-full max-w-md flex-col gap-4 rounded bg-background p-6 shadow-lg">
        <h2 className="text-lg font-semibold">移动 {source.name}</h2>
        <p className="text-sm text-muted-foreground">选择新的上级部门：</p>
        <div className="max-h-80 overflow-auto rounded border p-2">
          <Tree<DepartmentNode>
            nodes={tree}
            getId={(n) => n.id}
            getChildren={(n) => n.children}
            renderNode={(n) => (
              <span className={blocked.has(n.id) ? "text-muted-foreground" : ""}>
                {n.name}
              </span>
            )}
            expandedIds={expanded}
            onExpandChange={setExpanded}
            onSelect={(n) => {
              if (!blocked.has(n.id)) setTargetId(n.id);
            }}
            selectedId={targetId}
          />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            取消
          </Button>
          <Button
            type="button"
            disabled={!targetId || submitting}
            onClick={onSubmit}
          >
            确认移动
          </Button>
        </div>
      </div>
    </div>
  );
}
