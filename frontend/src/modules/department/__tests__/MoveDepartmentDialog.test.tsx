import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MoveDepartmentDialog } from "../components/MoveDepartmentDialog";
import type { DepartmentNode } from "../types";

vi.mock("../api", () => ({ moveDepartment: vi.fn().mockResolvedValue({}) }));
import * as api from "../api";

const src: DepartmentNode = {
  id: "s1",
  parentId: null,
  name: "Source",
  path: "/s/",
  depth: 0,
  isActive: true,
  children: [],
};
const tree: DepartmentNode[] = [
  src,
  {
    id: "t1",
    parentId: null,
    name: "Target",
    path: "/t/",
    depth: 0,
    isActive: true,
    children: [],
  },
];

describe("MoveDepartmentDialog", () => {
  beforeEach(() => vi.clearAllMocks());

  it("disables submit until a target is chosen", () => {
    render(
      <MoveDepartmentDialog
        source={src}
        tree={tree}
        onClose={() => {}}
        onMoved={() => {}}
      />,
    );
    const submit = screen.getByRole("button", { name: "确认移动" });
    expect(submit).toBeDisabled();
  });

  it("POSTs to move endpoint on submit", async () => {
    const onMoved = vi.fn();
    render(
      <MoveDepartmentDialog
        source={src}
        tree={tree}
        onClose={() => {}}
        onMoved={onMoved}
      />,
    );
    await userEvent.click(screen.getByText("Target"));
    await userEvent.click(screen.getByRole("button", { name: "确认移动" }));
    expect(api.moveDepartment).toHaveBeenCalledWith("s1", { newParentId: "t1" });
  });
});
