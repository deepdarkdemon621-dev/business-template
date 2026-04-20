import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "@/components/layout/Sidebar";

vi.mock("@/modules/rbac/usePermissions", () => ({
  usePermissions: vi.fn(),
}));
import { usePermissions } from "@/modules/rbac/usePermissions";

describe("Sidebar", () => {
  it("renders only nav entries user has permission for", () => {
    (usePermissions as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      has: (code: string) => code === "user:list",
      isLoading: false,
    });

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText(/用户/i)).toBeInTheDocument();
    // "部门" nav is gated by department:list — not granted here
    expect(screen.queryByText(/部门/i)).not.toBeInTheDocument();
  });

  it("shows nothing behind a gate when user has no permissions", () => {
    (usePermissions as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      has: () => false,
      isLoading: false,
    });

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.queryByText(/用户/i)).not.toBeInTheDocument();
  });
});
