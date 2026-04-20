import { NavLink } from "react-router-dom";
import { usePermissions } from "@/modules/rbac/usePermissions";
import { NAV_ITEMS } from "./nav-items";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const { has, isLoading } = usePermissions();
  if (isLoading) return null;
  const visible = NAV_ITEMS.filter(
    (i) => !i.requiredPermission || has(i.requiredPermission)
  );

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r bg-muted/20 p-4">
      <nav aria-label="Main navigation" className="flex flex-col gap-1">
        {visible.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "rounded px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-accent hover:text-accent-foreground"
              )
            }
            end={item.path === "/"}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
