import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Tree, type TreeNode } from "../tree";

type Dept = { id: string; name: string; children?: Dept[] };

const data: Dept[] = [
  {
    id: "a",
    name: "A",
    children: [
      { id: "a1", name: "A1", children: [{ id: "a11", name: "A11" }] },
    ],
  },
  { id: "b", name: "B" },
];

function Harness({ onSelect }: { onSelect?: (id: string) => void }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  return (
    <Tree<Dept>
      nodes={data as TreeNode<Dept>[]}
      getId={(n) => n.id}
      getChildren={(n) => n.children ?? []}
      renderNode={(n) => <span>{n.name}</span>}
      expandedIds={expanded}
      onExpandChange={setExpanded}
      onSelect={(n) => onSelect?.(n.id)}
    />
  );
}

describe("Tree", () => {
  it("renders top-level nodes", () => {
    render(<Harness />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    // Deeper levels are hidden when expandedIds is empty.
    expect(screen.queryByText("A1")).not.toBeInTheDocument();
  });

  it("expands when the toggle is clicked", async () => {
    render(<Harness />);
    // Each expandable node exposes a button labeled with its own name.
    const toggle = screen.getAllByRole("button", { name: /^展开 A$/ })[0]!;
    await userEvent.click(toggle);
    expect(screen.getByText("A1")).toBeInTheDocument();
  });

  it("invokes onSelect with the clicked node", async () => {
    const onSelect = vi.fn();
    render(<Harness onSelect={onSelect} />);
    await userEvent.click(screen.getByText("B"));
    expect(onSelect).toHaveBeenCalledWith("b");
  });
});
