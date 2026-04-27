import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { listUsers } from "@/modules/user/api";
import type { User } from "@/modules/user/types";

interface Props {
  value: string | undefined;
  onChange: (userId: string | undefined) => void;
}

export function ActorAutocomplete({ value, onChange }: Props) {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);

  // V1 note: when `value` is set from URL state on mount, the input shows empty
  // until the user types. A "look up by id and display email" prefetch would
  // improve this but is deferred until it can be properly tested.

  useEffect(() => {
    if (!query.trim()) {
      setMatches([]);
      return;
    }
    let active = true;
    setLoading(true);
    listUsers({ page: 1, size: 8, q: query })
      .then((p) => active && setMatches(p.items))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [query]);

  return (
    <div className="relative">
      <Input
        placeholder="Actor (email)"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-56"
      />
      {query && matches.length > 0 ? (
        <ul className="absolute z-10 mt-1 w-56 rounded border bg-popover shadow-md text-sm">
          {matches.map((u) => (
            <li key={u.id}>
              <button
                type="button"
                className="block w-full px-2 py-1 text-left hover:bg-muted"
                onClick={() => {
                  onChange(u.id);
                  setQuery(u.email);
                  setMatches([]);
                }}
              >
                {u.fullName}{" "}
                <span className="text-muted-foreground">({u.email})</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {value ? (
        <button
          type="button"
          className="absolute right-1 top-1 text-xs text-muted-foreground"
          onClick={() => {
            onChange(undefined);
            setQuery("");
          }}
          aria-label="Clear actor"
        >
          ✕
        </button>
      ) : null}
      {loading ? (
        <div className="text-xs text-muted-foreground mt-1">Searching…</div>
      ) : null}
    </div>
  );
}
