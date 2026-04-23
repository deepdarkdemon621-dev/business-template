import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { RoleEditPage } from "../RoleEditPage";
import * as api from "../api";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/roles/new" element={<RoleEditPage />} />
        <Route path="/admin/roles/:id" element={<RoleEditPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RoleEditPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "listPermissions").mockResolvedValue([
      { id: "p1", code: "user:read", resource: "user", action: "read", description: null },
    ]);
  });

  it("renders create mode with empty form fields", async () => {
    renderAt("/admin/roles/new");
    await waitFor(() => {
      // Schema title "Code" is rendered as a label; input is present
      expect(screen.getByLabelText(/code/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    });
  });

  it("shows read-only banner when role is superadmin", async () => {
    vi.spyOn(api, "getRole").mockResolvedValue({
      id: "su",
      code: "superadmin",
      name: "Super Administrator",
      isBuiltin: true,
      isSuperadmin: true,
      permissions: [],
      userCount: 1,
      updatedAt: "2026-04-22T00:00:00Z",
    });
    renderAt("/admin/roles/su");
    await waitFor(() => {
      expect(screen.getByText(/immutable/i)).toBeInTheDocument();
    });
    // No form inputs rendered.
    expect(screen.queryByRole("textbox", { name: /code/i })).not.toBeInTheDocument();
  });

  it("renders form + matrix for non-superadmin builtin (admin)", async () => {
    vi.spyOn(api, "getRole").mockResolvedValue({
      id: "ad",
      code: "admin",
      name: "Admin",
      isBuiltin: true,
      isSuperadmin: false,
      permissions: [{ permissionCode: "user:read", scope: "global" }],
      userCount: 1,
      updatedAt: "2026-04-22T00:00:00Z",
    });
    renderAt("/admin/roles/ad");
    await waitFor(() => {
      expect(screen.getByLabelText(/code/i)).toBeInTheDocument();
    });
    // Matrix is editable (radios enabled).
    const radios = screen.getAllByRole("radio");
    radios.forEach((r) => expect(r).not.toBeDisabled());
  });
});
