import { useEffect, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { getAuditEvent } from "@/modules/audit/api";
import type { AuditEventDetail as AuditEventDetailType } from "@/modules/audit/types";
import { DiffView } from "./DiffView";

interface Props {
  eventId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AuditEventDetail({ eventId, open, onOpenChange }: Props) {
  const [event, setEvent] = useState<AuditEventDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventId || !open) return;
    let active = true;
    setEvent(null);
    setError(null);
    getAuditEvent(eventId)
      .then((e) => { if (active) setEvent(e); })
      .catch((err: unknown) => {
        if (active) {
          const msg =
            err instanceof Error ? err.message : "Failed to load";
          setError(msg);
        }
      });
    return () => {
      active = false;
    };
  }, [eventId, open]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Audit event</SheetTitle>
        </SheetHeader>
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : null}
        {event ? (
          <div className="flex flex-col gap-4 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">Occurred at</div>
              <div>{new Date(event.occurredAt).toLocaleString()}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Event</div>
              <div className="font-mono">{event.eventType}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Actor</div>
              {event.actor ? (
                <div>
                  {event.actor.name}{" "}
                  <span className="text-muted-foreground">
                    ({event.actor.email})
                  </span>
                </div>
              ) : (
                <div className="text-muted-foreground">—</div>
              )}
              {event.actorIp ? (
                <div className="text-xs text-muted-foreground">
                  IP: {event.actorIp}
                </div>
              ) : null}
              {event.actorUserAgent ? (
                <div
                  className="text-xs text-muted-foreground truncate"
                  title={event.actorUserAgent}
                >
                  UA: {event.actorUserAgent}
                </div>
              ) : null}
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Resource</div>
              <div>
                {event.resourceType
                  ? `${event.resourceType}: ${event.resourceLabel ?? "—"}`
                  : "—"}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Summary</div>
              <div>{event.summary}</div>
            </div>
            <DiffView
              action={event.action}
              before={event.before}
              after={event.after}
              changes={
                event.changes as Record<string, [unknown, unknown]> | null
              }
            />
            {event.metadata && Object.keys(event.metadata).length > 0 ? (
              <div>
                <div className="text-xs text-muted-foreground">Metadata</div>
                <pre className="rounded bg-muted p-3 text-xs overflow-x-auto">
                  {JSON.stringify(event.metadata, null, 2)}
                </pre>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Loading…</p>
        )}
      </SheetContent>
    </Sheet>
  );
}
