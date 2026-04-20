import { useEffect, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { listRoles } from "../api";
import type { RoleSummary } from "../types";

export type RoleAssignmentPanelProps = {
  initialRoleIds: string[];
  onSelectionChange: (roleIds: string[]) => void;
};

export function RoleAssignmentPanel({
  initialRoleIds,
  onSelectionChange,
}: RoleAssignmentPanelProps) {
  const [available, setAvailable] = useState<RoleSummary[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(initialRoleIds));
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void listRoles().then((rs) => {
      if (!active) return;
      setAvailable(rs);
      setLoaded(true);
    });
    return () => {
      active = false;
    };
  }, []);

  function toggle(roleId: string) {
    const next = new Set(selected);
    if (next.has(roleId)) next.delete(roleId);
    else next.add(roleId);
    setSelected(next);
    onSelectionChange(Array.from(next));
  }

  if (!loaded) return <p className="text-sm text-muted-foreground">加载角色…</p>;

  return (
    <fieldset className="flex flex-col gap-2 rounded border p-4">
      <legend className="px-1 text-sm font-medium">角色</legend>
      {available.map((r) => {
        const id = `role-${r.id}`;
        return (
          <div key={r.id} className="flex items-center gap-2">
            <Checkbox
              id={id}
              checked={selected.has(r.id)}
              onCheckedChange={() => toggle(r.id)}
            />
            <Label htmlFor={id} className="text-sm font-normal">
              {r.name}{" "}
              <span className="text-muted-foreground">({r.code})</span>
            </Label>
          </div>
        );
      })}
    </fieldset>
  );
}
