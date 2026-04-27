import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/modules/audit/api", () => ({
  listAuditEvents: vi.fn(),
  getAuditEvent: vi.fn(),
}));
vi.mock("@/modules/user/api", () => ({
  listUsers: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, size: 8, hasNext: false }),
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

  it("passes event_type filter to the API when user selects an event", async () => {
    (listAuditEvents as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [], total: 0, page: 1, size: 20, hasNext: false,
    });
    render(
      <MemoryRouter>
        <AuditLogPage />
      </MemoryRouter>,
    );
    // wait for initial render
    await waitFor(() => expect(listAuditEvents).toHaveBeenCalled());
    // open event-type select, pick "user.created"
    const trigger = screen.getByRole("button", { name: /event type/i });
    trigger.click();
    const option = await screen.findByText("user.created");
    option.click();
    // assert next API call carried event_type filter
    await waitFor(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- vi.fn mock introspection
      const lastCall = (listAuditEvents as any).mock.calls.at(-1);
      expect(lastCall[1].eventType).toContain("user.created");
    });
  });
});
