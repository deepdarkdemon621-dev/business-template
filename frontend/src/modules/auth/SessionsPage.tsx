import { useCallback, useEffect, useState } from "react";
import { client } from "@/api/client";
import type { Page } from "@/lib/pagination";

interface Session {
  id: string;
  deviceLabel: string | null;
  ipAddress: string | null;
  createdAt: string;
  lastUsedAt: string;
  expiresAt: string;
  isCurrent: boolean;
}

export function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    const { data } = await client.get<Page<Session>>("/me/sessions", {
      params: { page: 1, size: 50 },
    });
    setSessions(data.items);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const revoke = async (id: string) => {
    await client.delete(`/me/sessions/${id}`);
    await loadSessions();
  };

  if (loading) return <div className="p-8">Loading sessions...</div>;

  return (
    <div className="mx-auto mt-10 max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">Active Sessions</h1>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="pb-2">Device</th>
            <th className="pb-2">IP</th>
            <th className="pb-2">Last Used</th>
            <th className="pb-2" />
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.id} className="border-b">
              <td className="py-2">
                {s.deviceLabel ?? "Unknown"}{" "}
                {s.isCurrent && (
                  <span className="ml-1 text-xs font-medium text-green-600">(current)</span>
                )}
              </td>
              <td className="py-2">{s.ipAddress ?? "—"}</td>
              <td className="py-2">{new Date(s.lastUsedAt).toLocaleString()}</td>
              <td className="py-2">
                {!s.isCurrent && (
                  <button
                    onClick={() => revoke(s.id)}
                    className="text-sm text-red-600 hover:underline"
                  >
                    Revoke
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
