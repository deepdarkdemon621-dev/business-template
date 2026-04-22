import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DepartmentListPage } from "../DepartmentListPage";

vi.mock("../api", () => ({
  getDepartmentTree: vi.fn(),
  softDeleteDepartment: vi.fn(),
}));
import * as api from "../api";

describe("DepartmentListPage", () => {
  beforeEach(() => {
    vi.mocked(api.getDepartmentTree).mockResolvedValue([
      {
        id: "r1",
        parentId: null,
        name: "Root",
        path: "/root/",
        depth: 0,
        isActive: true,
        children: [
          {
            id: "c1",
            parentId: "r1",
            name: "Child",
            path: "/root/child/",
            depth: 1,
            isActive: true,
            children: [],
          },
        ],
      },
    ]);
  });

  it("fetches and renders the tree", async () => {
    render(
      <MemoryRouter>
        <DepartmentListPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Root")).toBeInTheDocument();
    });
  });
});
