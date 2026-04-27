interface Props {
  action: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  changes: Record<string, [unknown, unknown]> | null;
}

function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export function DiffView({ action, before, after, changes }: Props) {
  if (action === "create" && after) {
    return (
      <pre className="rounded bg-muted p-3 text-xs border-l-4 border-l-green-500 overflow-x-auto">
        {JSON.stringify(after, null, 2)}
      </pre>
    );
  }
  if (action === "delete" && before) {
    return (
      <pre className="rounded bg-muted p-3 text-xs border-l-4 border-l-red-500 overflow-x-auto">
        {JSON.stringify(before, null, 2)}
      </pre>
    );
  }
  if (action === "update" && changes && Object.keys(changes).length > 0) {
    return (
      <table className="w-full border-collapse text-xs">
        <tbody>
          {Object.entries(changes).map(([field, [oldVal, newVal]]) => (
            <tr key={field} className="border-b last:border-0">
              <td className="py-1 pr-3 font-mono">{field}</td>
              <td className="py-1 px-3">{fmt(oldVal)}</td>
              <td className="py-1 px-1 text-muted-foreground">→</td>
              <td className="py-1 pl-3">{fmt(newVal)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  return null;
}
