import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/modules/user/api", () => ({
  createUser: vi.fn(),
  getUser: vi.fn(),
  updateUser: vi.fn(),
  listRoles: vi.fn().mockResolvedValue([]),
  assignRole: vi.fn(),
  revokeRole: vi.fn(),
}));
import {
  assignRole,
  createUser,
  getUser,
  listRoles,
  revokeRole,
  updateUser,
} from "@/modules/user/api";
import { UserEditPage } from "@/modules/user/UserEditPage";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("UserEditPage create mode", () => {
  it("submits a valid payload and navigates on success", async () => {
    (createUser as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "new",
      email: "c@ex.com",
      fullName: "C",
      departmentId: null,
      isActive: true,
      mustChangePassword: true,
      createdAt: "2026-04-20T00:00:00Z",
      updatedAt: "2026-04-20T00:00:00Z",
    });

    render(
      <MemoryRouter initialEntries={["/admin/users/new"]}>
        <Routes>
          <Route path="/admin/users/new" element={<UserEditPage mode="create" />} />
          <Route path="/admin/users/:id" element={<div>detail</div>} />
        </Routes>
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/邮箱|email/i), "c@ex.com");
    await userEvent.type(screen.getByLabelText(/姓名|full name/i), "C");
    await userEvent.type(screen.getByLabelText(/^密码$|password/i), "GoodOne123");

    await userEvent.click(screen.getByRole("button", { name: /创建|create/i }));

    await waitFor(() => expect(createUser).toHaveBeenCalledTimes(1));
    expect(createUser).toHaveBeenCalledWith(
      expect.objectContaining({ email: "c@ex.com", fullName: "C", password: "GoodOne123" })
    );
  });
});

describe("UserEditPage edit mode", () => {
  it("loads user, shows current roles, diffs and commits role changes on save", async () => {
    (getUser as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "u1",
      email: "e@ex.com",
      fullName: "E",
      departmentId: null,
      isActive: true,
      mustChangePassword: false,
      createdAt: "2026-04-20T00:00:00Z",
      updatedAt: "2026-04-20T00:00:00Z",
      roles: [{ id: "r1", code: "member", name: "Member" }],
      department: null,
    });
    (listRoles as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: "r1", code: "member", name: "Member" },
      { id: "r2", code: "admin", name: "Admin" },
    ]);
    (updateUser as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({});
    (assignRole as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    (revokeRole as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    render(
      <MemoryRouter initialEntries={["/admin/users/u1"]}>
        <Routes>
          <Route path="/admin/users/:id" element={<UserEditPage mode="edit" />} />
          <Route path="/admin/users" element={<div>list</div>} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByDisplayValue("E")).toBeInTheDocument());

    // Member is currently checked; Admin is not. Toggle: uncheck member, check admin.
    // findByRole awaits the role panel's own listRoles() resolve; getByRole is
    // synchronous and races the separate fetch microtask under load.
    await userEvent.click(await screen.findByRole("checkbox", { name: /member/i }));
    await userEvent.click(screen.getByRole("checkbox", { name: /admin/i }));

    await userEvent.click(screen.getByRole("button", { name: /保存|save/i }));

    await waitFor(() => expect(updateUser).toHaveBeenCalled());
    expect(revokeRole).toHaveBeenCalledWith("u1", "r1");
    expect(assignRole).toHaveBeenCalledWith("u1", "r2");
  });
});
