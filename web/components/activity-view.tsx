"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { listActivity, listNotebooks, type NotebookSummary } from "@/lib/api";
import { activityLabel, type ActivityEvent } from "@/lib/activity";

type Load =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; events: ActivityEvent[] };

export function ActivityView() {
  const [notebooks, setNotebooks] = useState<NotebookSummary[]>([]);
  const [scopeId, setScopeId] = useState("brain");
  const [load, setLoad] = useState<Load>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    listNotebooks()
      .then((rows) => {
        if (!cancelled) setNotebooks(rows);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    listActivity(scopeId === "brain" ? undefined : scopeId)
      .then((events) => {
        if (!cancelled) setLoad({ kind: "ready", events });
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setLoad({
            kind: "error",
            message:
              err instanceof Error ? err.message : "Something went wrong.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, [scopeId]);

  return (
    <div className="space-y-6">
      <label className="flex items-center gap-2 text-sm">
        <span className="text-muted-foreground">Show</span>
        <Select
          aria-label="Activity scope"
          value={scopeId}
          onChange={(e) => {
            setLoad({ kind: "loading" });
            setScopeId(e.target.value);
          }}
        >
          <option value="brain">Whole Brain</option>
          {notebooks.map((n) => (
            <option key={n.id} value={n.id}>
              {n.name}
            </option>
          ))}
        </Select>
      </label>
      {load.kind === "loading" ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : null}
      {load.kind === "error" ? (
        <p role="alert" className="text-sm text-red-500 dark:text-red-400">
          {load.message}
        </p>
      ) : null}
      {load.kind === "ready" && load.events.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nothing has happened here yet.
        </p>
      ) : null}
      {load.kind === "ready" && load.events.length > 0 ? (
        <ul className="space-y-2">
          {load.events.map((e) => (
            <li
              key={e.id}
              className="flex items-center gap-3 rounded-xl border border-border px-4 py-2 text-sm"
            >
              <Badge
                variant={e.kind === "removed" ? "destructive" : "secondary"}
              >
                {activityLabel(e.kind)}
              </Badge>
              <span className="min-w-0 flex-1 truncate">{e.source_name}</span>
              <time
                dateTime={e.created_at}
                className="text-xs text-muted-foreground"
              >
                {new Date(e.created_at).toLocaleString()}
              </time>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
