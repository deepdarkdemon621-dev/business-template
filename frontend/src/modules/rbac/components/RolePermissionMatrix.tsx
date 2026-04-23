import { useMemo } from "react";
import { RadioOption } from "@/components/ui/radio-option";
import type { Permission, RolePermissionItem, Scope } from "../types";

const SCOPE_CHOICES: { label: string; value: Scope | null }[] = [
  { label: "Not granted", value: null },
  { label: "own", value: "own" },
  { label: "dept", value: "dept" },
  { label: "dept_tree", value: "dept_tree" },
  { label: "global", value: "global" },
];

export interface RolePermissionMatrixProps {
  value: RolePermissionItem[];
  onChange: (next: RolePermissionItem[]) => void;
  allPermissions: Permission[];
  disabled?: boolean;
}

export function RolePermissionMatrix({
  value,
  onChange,
  allPermissions,
  disabled = false,
}: RolePermissionMatrixProps) {
  const currentScope = useMemo(() => {
    const m = new Map<string, Scope>();
    for (const v of value) m.set(v.permissionCode, v.scope);
    return m;
  }, [value]);

  const grouped = useMemo(() => {
    const m = new Map<string, Permission[]>();
    for (const p of allPermissions) {
      if (!m.has(p.resource)) m.set(p.resource, []);
      m.get(p.resource)!.push(p);
    }
    return Array.from(m.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [allPermissions]);

  function handleSelect(permissionCode: string, scope: Scope | null) {
    const next = value.filter((v) => v.permissionCode !== permissionCode);
    if (scope !== null) next.push({ permissionCode, scope });
    onChange(next);
  }

  return (
    <div className="space-y-4">
      {grouped.map(([resource, perms]) => {
        const grantedCount = perms.filter((p) => currentScope.has(p.code)).length;
        return (
          <details key={resource} open className="rounded border border-border">
            <summary className="cursor-pointer select-none p-3 font-medium capitalize">
              {resource} ({grantedCount}/{perms.length})
            </summary>
            <div className="border-t border-border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-left">
                  <tr>
                    <th className="p-2 font-mono text-xs">Code</th>
                    <th className="p-2">Description</th>
                    {SCOPE_CHOICES.map((c) => (
                      <th key={c.label} className="p-2 text-center text-xs">
                        {c.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {perms.map((p) => {
                    const current = currentScope.get(p.code) ?? null;
                    return (
                      <tr key={p.id} className="border-t border-border">
                        <td className="p-2 font-mono text-xs">{p.code}</td>
                        <td className="p-2 text-muted-foreground">{p.description}</td>
                        {SCOPE_CHOICES.map((c) => (
                          <td key={c.label} className="p-2 text-center">
                            <RadioOption
                              name={`perm-${p.code}`}
                              aria-label={`${p.code} ${c.label}`}
                              checked={current === c.value}
                              disabled={disabled}
                              onChange={() => handleSelect(p.code, c.value)}
                            />
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>
        );
      })}
    </div>
  );
}
