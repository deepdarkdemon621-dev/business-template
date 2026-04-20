import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/modules/user/api", () => ({
  createUser: vi.fn(),
  getUser: vi.fn(),
  updateUser: vi.fn(),
  listRoles: vi.fn().mockResolvedValue([]),
  assignRole: vi.fn(),
  revokeRole: vi.fn(),
}));
import { createUser } from "@/modules/user/api";
import { UserEditPage } from "@/modules/user/UserEditPage";

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
