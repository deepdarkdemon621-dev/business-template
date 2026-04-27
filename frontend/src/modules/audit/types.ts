export interface AuditActor {
  id: string;
  email: string;
  name: string;
}

export interface AuditEvent {
  id: string;
  occurredAt: string;
  eventType: string;
  action: string;
  actor: AuditActor | null;
  actorIp: string | null;
  actorUserAgent: string | null;
  resourceType: string | null;
  resourceId: string | null;
  resourceLabel: string | null;
  summary: string;
}

export interface AuditEventDetail extends AuditEvent {
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  changes: Record<string, [unknown, unknown]> | null;
  metadata: Record<string, unknown> | null;
}

export interface AuditFilters {
  occurredFrom?: string;
  occurredTo?: string;
  eventType?: string[];
  action?: string[];
  actorUserId?: string;
  resourceType?: string;
  resourceId?: string;
  q?: string;
}
