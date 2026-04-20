import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DataTable, type ColumnDef } from "@/components/table/DataTable";

type Row = { id: string; name: string };

const columns: ColumnDef<Row>[] = [
  { key: "name", header: "Name", render: (r) => r.name },
];

function makePage(items: Row[], page = 1, total = items.length) {
  return { items, total, page, size: 20, hasNext: total > page * 20 };
}

describe("DataTable", () => {
  it("renders loading state then rows", async () => {
    const fetcher = vi.fn().mockResolvedValue(makePage([{ id: "1", name: "Alice" }]));
    render(<DataTable columns={columns} fetcher={fetcher} queryKey={["users"]} />);
    expect(screen.getByRole("status", { name: /loading/i })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Alice")).toBeInTheDocument());
  });

  it("renders empty state when no rows", async () => {
    const fetcher = vi.fn().mockResolvedValue(makePage([]));
    render(<DataTable columns={columns} fetcher={fetcher} queryKey={["users"]} />);
    await waitFor(() =>
      expect(screen.getByText(/no results/i)).toBeInTheDocument()
    );
  });

  it("calls fetcher with page=2 after Next click", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(makePage([{ id: "1", name: "A" }], 1, 25))
      .mockResolvedValueOnce(makePage([{ id: "2", name: "B" }], 2, 25));
    render(<DataTable columns={columns} fetcher={fetcher} queryKey={["users"]} />);
    await waitFor(() => expect(screen.getByText("A")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => expect(screen.getByText("B")).toBeInTheDocument());

    expect(fetcher).toHaveBeenNthCalledWith(1, expect.objectContaining({ page: 1 }));
    expect(fetcher).toHaveBeenNthCalledWith(2, expect.objectContaining({ page: 2 }));
  });

  it("renders error state on fetch rejection", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("boom"));
    render(<DataTable columns={columns} fetcher={fetcher} queryKey={["users"]} />);
    await waitFor(() =>
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    );
  });
});
