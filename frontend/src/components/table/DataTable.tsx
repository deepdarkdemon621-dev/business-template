import { useEffect, useState, type ReactNode } from "react";
import type { Page, PageQuery } from "@/lib/pagination";
import { Button } from "@/components/ui/button";

export type ColumnDef<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  sortable?: boolean;
};

export type DataTableProps<T> = {
  columns: ColumnDef<T>[];
  fetcher: (pq: PageQuery) => Promise<Page<T>>;
  queryKey: readonly unknown[];
  initialSize?: number;
  rowActions?: (row: T) => ReactNode;
  emptyMessage?: string;
};

type Status = "idle" | "loading" | "error" | "ready";

/**
 * Server-paginated table. Pass a new `queryKey` tuple to trigger a refetch
 * (e.g. after a mutation).
 */
export function DataTable<T extends { id: string }>({
  columns,
  fetcher,
  queryKey,
  initialSize = 20,
  rowActions,
  emptyMessage = "No results.",
}: DataTableProps<T>) {
  const [page, setPage] = useState(1);
  const [size] = useState(initialSize);
  const [data, setData] = useState<Page<T> | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    (async () => {
      setStatus("loading");
      try {
        const result = await fetcher({ page, size });
        if (!active) return;
        setData(result);
        setStatus("ready");
      } catch {
        if (active) setStatus("error");
      }
    })();
    return () => {
      active = false;
    };
    // queryKey is intentionally spread so caller can trigger re-fetch by passing a new tuple.
  }, [fetcher, page, size, reloadToken, ...queryKey]);

  if (status === "loading" && !data) {
    return (
      <div role="status" aria-label="Loading" className="py-8 text-center text-muted-foreground">
        Loading…
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="py-8 text-center text-destructive">
        Failed to load.{" "}
        <Button variant="ghost" size="sm" onClick={() => setReloadToken((t) => t + 1)}>
          Retry
        </Button>
      </div>
    );
  }
  if (!data || data.items.length === 0) {
    return <div className="py-8 text-center text-muted-foreground">{emptyMessage}</div>;
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-x-auto rounded border">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              {columns.map((c) => (
                <th key={c.key} scope="col" className="px-3 py-2 text-left font-medium">
                  {c.header}
                </th>
              ))}
              {rowActions ? <th scope="col" className="px-3 py-2" /> : null}
            </tr>
          </thead>
          <tbody>
            {data.items.map((row) => (
              <tr key={row.id} className="border-t">
                {columns.map((c) => (
                  <td key={c.key} className="px-3 py-2">
                    {c.render(row)}
                  </td>
                ))}
                {rowActions ? <td className="px-3 py-2 text-right">{rowActions(row)}</td> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Page {data.page} of {Math.max(1, Math.ceil(data.total / data.size))} · {data.total} total
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!data.hasNext}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
