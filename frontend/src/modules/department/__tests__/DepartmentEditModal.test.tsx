import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DepartmentEditModal } from "../components/DepartmentEditModal";

vi.mock("../api", () => ({
  createDepartment: vi.fn().mockResolvedValue({}),
  updateDepartment: vi.fn().mockResolvedValue({}),
}));
import * as api from "../api";

describe("DepartmentEditModal", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creates via POST when mode=create", async () => {
    const onSaved = vi.fn();
    render(
      <DepartmentEditModal
        state={{ mode: "create", parentId: "p1" }}
        onClose={() => {}}
        onSaved={onSaved}
      />,
    );
    await userEvent.type(screen.getByLabelText("部门名称"), "NewDept");
    await userEvent.click(screen.getByRole("button", { name: "保存" }));
    expect(api.createDepartment).toHaveBeenCalledWith({
      name: "NewDept",
      parentId: "p1",
    });
  });

  it("blocks submit when name is empty (ajv)", async () => {
    const onSaved = vi.fn();
    render(
      <DepartmentEditModal
        state={{ mode: "create", parentId: "p1" }}
        onClose={() => {}}
        onSaved={onSaved}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "保存" }));
    expect(api.createDepartment).not.toHaveBeenCalled();
  });
});
