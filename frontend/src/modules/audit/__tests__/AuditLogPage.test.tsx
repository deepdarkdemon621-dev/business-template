import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/modules/audit/api", () => ({
  listAuditEvents: vi.fn(),
  getAuditEvent: vi.fn(),
}));
import { listAuditEvents } from "@/modules/audit/api";
import { AuditLogPage } from "@/modules/audit/AuditLogPage";

describe("AuditLogPage", () => {
  it("renders table rows from the API", async () => {
    (listAuditEvents as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: "e1",
          occurredAt: "2026-04-24T12:00:00Z",
          eventType: "user.created",
          action: "create",
          actor: { id: "u1", email: "admin@x", name: "Admin" },
          actorIp: "10.0.0.1",
          actorUserAgent: "ua",
          resourceType: "user",
          resourceId: "u2",
          resourceLabel: "new@x",
          summary: "Created user 'new@x'",
        },
      ],
      total: 1,
      page: 1,
      size: 20,
      hasNext: false,
    });
    render(
      <MemoryRouter>
        <AuditLogPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByText("Created user 'new@x'")).toBeInTheDocument(),
    );
    expect(screen.getByText("admin@x")).toBeInTheDocument();
  });
});
