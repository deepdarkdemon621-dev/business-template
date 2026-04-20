import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/modules/user/api", () => ({
  listUsers: vi.fn(),
}));
vi.mock("@/modules/rbac/usePermissions", () => ({
  usePermissions: () => ({ can: () => true, isLoading: false }),
}));
import { listUsers } from "@/modules/user/api";
import { UserListPage } from "@/modules/user/UserListPage";

describe("UserListPage", () => {
  it("renders rows for users returned from the API", async () => {
    (listUsers as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: "u1",
          email: "a@b.com",
          fullName: "Alice",
          departmentId: null,
          isActive: true,
          mustChangePassword: false,
          createdAt: "2026-04-20T00:00:00Z",
          updatedAt: "2026-04-20T00:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      size: 20,
      hasNext: false,
    });

    render(
      <MemoryRouter>
        <UserListPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Alice")).toBeInTheDocument());
    expect(screen.getByText("a@b.com")).toBeInTheDocument();
  });
});
