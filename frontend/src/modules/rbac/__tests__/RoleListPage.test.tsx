import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { RoleListPage } from "../RoleListPage";
import * as api from "../api";

function renderPage() {
  return render(
    <MemoryRouter>
      <RoleListPage />
    </MemoryRouter>,
  );
}

describe("RoleListPage", () => {
  beforeEach(() => {
    vi.spyOn(api, "listRoles").mockResolvedValue({
      items: [
        {
          id: "r1",
          code: "admin",
          name: "Admin",
          isBuiltin: true,
          isSuperadmin: false,
          userCount: 1,
          permissionCount: 18,
          updatedAt: "2026-04-22T00:00:00Z",
        },
        {
          id: "r2",
          code: "tester",
          name: "Tester",
          isBuiltin: false,
          isSuperadmin: false,
          userCount: 3,
          permissionCount: 2,
          updatedAt: "2026-04-22T00:00:00Z",
        },
      ],
      total: 2,
      page: 1,
      size: 20,
      hasNext: false,
    });
  });

  it("renders roles with counts", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("admin")).toBeInTheDocument();
      expect(screen.getByText("tester")).toBeInTheDocument();
    });
  });

  it("disables delete on builtin", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("admin")).toBeInTheDocument());
    // The first row is admin (builtin); its delete button should be disabled.
    const deleteButtons = screen.getAllByRole("button", { name: /^delete$/i });
    expect(deleteButtons[0]).toBeDisabled(); // admin row
    expect(deleteButtons[1]).toBeEnabled();  // tester row
  });

  it("opens delete dialog with cascade count on tester click", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("tester")).toBeInTheDocument());
    const testerDel = screen.getAllByRole("button", { name: /^delete$/i })[1]!;
    fireEvent.click(testerDel);
    expect(await screen.findByText(/assigned to 3 users/i)).toBeInTheDocument();
  });
});
