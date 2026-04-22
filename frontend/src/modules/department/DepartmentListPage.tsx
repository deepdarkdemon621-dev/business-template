import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Tree } from "@/components/ui/tree";
import { problemMessage } from "@/lib/problem-details";
import { getDepartmentTree, softDeleteDepartment } from "./api";
import { DepartmentEditModal } from "./components/DepartmentEditModal";
import { MoveDepartmentDialog } from "./components/MoveDepartmentDialog";
import type { DepartmentNode } from "./types";

type EditState =
  | { mode: "idle" }
  | { mode: "create"; parentId: string }
  | { mode: "rename"; node: DepartmentNode }
  | { mode: "move"; node: DepartmentNode };

export function DepartmentListPage() {
  const [tree, setTree] = useState<DepartmentNode[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<DepartmentNode | null>(null);
  const [editState, setEditState] = useState<EditState>({ mode: "idle" });
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const data = await getDepartmentTree(includeInactive);
      setTree(data);
    } catch (err) {
      setError(problemMessage(err));
    }
  }, [includeInactive]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onDelete(n: DepartmentNode) {
    if (!window.confirm(`软删除 ${n.name}?`)) return;
    try {
      await softDeleteDepartment(n.id);
      await reload();
    } catch (err) {
      setError(problemMessage(err));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">部门管理</h1>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
          />
          显示已停用
        </label>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Tree<DepartmentNode>
        nodes={tree}
        getId={(n) => n.id}
        getChildren={(n) => n.children}
        renderNode={(n) => (
          <div className="flex w-full items-center justify-between gap-2">
            <span className={n.isActive ? "" : "text-muted-foreground line-through"}>
              {n.name}
            </span>
            <span className="flex gap-1" onClick={(e) => e.stopPropagation()}>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditState({ mode: "create", parentId: n.id })}
              >
                +
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditState({ mode: "rename", node: n })}
              >
                重命名
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditState({ mode: "move", node: n })}
              >
                移动
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onDelete(n)}
              >
                删除
              </Button>
            </span>
          </div>
        )}
        expandedIds={expanded}
        onExpandChange={setExpanded}
        onSelect={setSelected}
        selectedId={selected?.id ?? null}
      />
      {editState.mode === "create" || editState.mode === "rename" ? (
        <DepartmentEditModal
          state={editState}
          onClose={() => setEditState({ mode: "idle" })}
          onSaved={async () => {
            setEditState({ mode: "idle" });
            await reload();
          }}
        />
      ) : null}
      {editState.mode === "move" ? (
        <MoveDepartmentDialog
          source={editState.node}
          tree={tree}
          onClose={() => setEditState({ mode: "idle" })}
          onMoved={async () => {
            setEditState({ mode: "idle" });
            await reload();
          }}
        />
      ) : null}
    </div>
  );
}
