import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/modules/audit/api", () => ({
  getAuditEvent: vi.fn(),
}));
import { getAuditEvent } from "@/modules/audit/api";
import { AuditEventDetail } from "../components/AuditEventDetail";

describe("AuditEventDetail", () => {
  it("loads event by id and renders summary + diff", async () => {
    (getAuditEvent as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "e1",
      occurredAt: "2026-04-24T12:00:00Z",
      eventType: "user.updated",
      action: "update",
      actor: { id: "u1", email: "a@x", name: "A" },
      actorIp: "10.0.0.1",
      actorUserAgent: "ua",
      resourceType: "user",
      resourceId: "u2",
      resourceLabel: "target@x",
      summary: "Updated user 'target@x' (name)",
      before: null,
      after: null,
      changes: { name: ["Old", "New"] },
      metadata: null,
    });
    render(<AuditEventDetail eventId="e1" open onOpenChange={() => {}} />);
    await waitFor(() => expect(screen.getAllByText(/target@x/).length).toBeGreaterThan(0));
    expect(screen.getByText(/Updated user/)).toBeInTheDocument();
    expect(screen.getByText("Old")).toBeInTheDocument();
    expect(screen.getByText("New")).toBeInTheDocument();
  });
});
