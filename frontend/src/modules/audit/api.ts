import { client } from "@/api/client";
import type { Page, PageQuery } from "@/lib/pagination";
import type { AuditEvent, AuditEventDetail, AuditFilters } from "./types";

function toQueryParams(pq: PageQuery, f: AuditFilters): Record<string, unknown> {
  const params: Record<string, unknown> = { ...pq };
  if (f.occurredFrom) params.occurred_from = f.occurredFrom;
  if (f.occurredTo) params.occurred_to = f.occurredTo;
  if (f.eventType?.length) params.event_type = f.eventType;
  if (f.action?.length) params.action = f.action;
  if (f.actorUserId) params.actor_user_id = f.actorUserId;
  if (f.resourceType) params.resource_type = f.resourceType;
  if (f.resourceId) params.resource_id = f.resourceId;
  if (f.q) params.q = f.q;
  return params;
}

export async function listAuditEvents(
  pq: PageQuery,
  filters: AuditFilters = {},
): Promise<Page<AuditEvent>> {
  const { data } = await client.get<Page<AuditEvent>>("/audit-events", {
    params: toQueryParams(pq, filters),
  });
  return data;
}

export async function getAuditEvent(id: string): Promise<AuditEventDetail> {
  const { data } = await client.get<AuditEventDetail>(`/audit-events/${id}`);
  return data;
}
