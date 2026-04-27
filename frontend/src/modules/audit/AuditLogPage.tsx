import { useCallback, useState } from "react";
import { Eye } from "lucide-react";
import { DataTable, type ColumnDef } from "@/components/table/DataTable";
import { Button } from "@/components/ui/button";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import type { PageQuery } from "@/lib/pagination";
import { listAuditEvents } from "./api";
import type { AuditEvent, AuditFilters } from "./types";
import { AuditEventDetail } from "./components/AuditEventDetail";

const EVENT_PILL: Record<string, string> = {
  create: "bg-green-100 text-green-900",
  update: "bg-blue-100 text-blue-900",
  delete: "bg-red-100 text-red-900",
  login: "bg-gray-100 text-gray-900",
  login_failed: "bg-amber-100 text-amber-900",
};

// Default: no date restriction — show all recent events.
// The user can opt-in to a date range via the picker.
const defaultFilters = (): AuditFilters => ({});

const columns: ColumnDef<AuditEvent>[] = [
  {
    key: "occurredAt",
    header: "Occurred at",
    sortable: true,
    render: (r) => new Date(r.occurredAt).toLocaleString(),
  },
  {
    key: "eventType",
    header: "Event",
    render: (r) => (
      <span
        className={`rounded px-2 py-0.5 text-xs ${EVENT_PILL[r.action] ?? "bg-gray-50 text-gray-700"}`}
      >
        {r.eventType}
      </span>
    ),
  },
  {
    key: "actor",
    header: "Actor",
    render: (r) =>
      r.actor ? (
        <div>
          <div>{r.actor.name}</div>
          <div className="text-xs text-muted-foreground">{r.actor.email}</div>
        </div>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    key: "resource",
    header: "Resource",
    render: (r) =>
      r.resourceType ? (
        <span>
          <span className="text-xs text-muted-foreground">
            {r.resourceType}:
          </span>{" "}
          {r.resourceLabel ?? "—"}
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    key: "summary",
    header: "Summary",
    render: (r) => r.summary,
  },
  {
    key: "actorIp",
    header: "IP",
    render: (r) =>
      r.actorIp ?? <span className="text-muted-foreground">—</span>,
  },
];

export function AuditLogPage() {
  const [filters, setFilters] = useState<AuditFilters>(defaultFilters);
  const [detailId, setDetailId] = useState<string | null>(null);

  const fetcher = useCallback(
    (pq: PageQuery) => listAuditEvents(pq, filters),
    [filters],
  );

  const fromDate = filters.occurredFrom
    ? new Date(filters.occurredFrom)
    : undefined;
  const toDate = filters.occurredTo ? new Date(filters.occurredTo) : undefined;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Audit log</h1>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <DateRangePicker
          value={{ from: fromDate, to: toDate }}
          onChange={(v) =>
            setFilters((f) => ({
              ...f,
              occurredFrom: v.from?.toISOString(),
              occurredTo: v.to?.toISOString(),
            }))
          }
          placeholder="Date range"
        />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setFilters(defaultFilters())}
        >
          Reset filters
        </Button>
        {/* Event type, action, actor, resource filters planned for Task 16b.
            Backend already supports all of them via query params; this bar ships
            date range + reset only for V1. */}
      </div>
      <DataTable<AuditEvent>
        columns={columns}
        fetcher={fetcher}
        queryKey={["audit", JSON.stringify(filters)]}
        rowActions={(row) => (
          <Button
            variant="ghost"
            size="sm"
            aria-label="View event"
            onClick={() => setDetailId(row.id)}
          >
            <Eye className="h-4 w-4" />
          </Button>
        )}
      />
      <AuditEventDetail
        eventId={detailId}
        open={detailId !== null}
        onOpenChange={(o) => !o && setDetailId(null)}
      />
    </div>
  );
}
