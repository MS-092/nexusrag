"use client";

import { useEffect, useState } from "react";
import { fetchHealth, summarizeHealth, type Health } from "@/lib/health";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; health: Health };

export function HealthPanel() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((health) => !cancelled && setState({ kind: "ready", health }))
      .catch(
        (err: unknown) =>
          !cancelled &&
          setState({
            kind: "error",
            message: err instanceof Error ? err.message : "Unknown error",
          }),
      );
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === "loading") {
    return <p className="text-sm text-muted-foreground">Checking the API…</p>;
  }
  if (state.kind === "error") {
    return (
      <p role="alert" className="text-sm text-red-600 dark:text-red-400">
        {state.message}
      </p>
    );
  }
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
      {summarizeHealth(state.health).map((row) => (
        <div key={row.name} className="contents">
          <dt className="text-muted-foreground">{row.name}</dt>
          <dd className="font-medium">{row.status}</dd>
        </div>
      ))}
    </dl>
  );
}
