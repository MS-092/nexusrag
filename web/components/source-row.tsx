"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Source } from "@/lib/api";
import { formatSize, stateLabel } from "@/lib/sources";

interface SourceRowProps {
  source: Source;
  retrying: boolean;
  onOpen: (source: Source) => void;
  onRetry: (source: Source) => void;
}

export function SourceRow({
  source,
  retrying,
  onOpen,
  onRetry,
}: SourceRowProps) {
  return (
    <li className="flex items-center gap-3 rounded-xl border border-border px-4 py-3">
      <button
        type="button"
        onClick={() => onOpen(source)}
        className="min-w-0 flex-1 text-left motion-safe:transition-opacity motion-safe:active:opacity-70"
      >
        <span className="block truncate text-sm font-medium">
          {source.name}
        </span>
        <span className="block text-xs text-muted-foreground">
          {source.kind.toUpperCase()} · {formatSize(source.size)}
          {source.state === "ready" ? ` · ${source.chunk_count} chunks` : ""}
          {source.cache_hit ? " · from cache" : ""}
        </span>
        {source.state === "failed" && source.error ? (
          <span
            role="alert"
            className="mt-1 block text-xs text-red-500 dark:text-red-400"
          >
            {source.error}
          </span>
        ) : null}
      </button>
      <Badge
        variant={source.state === "failed" ? "destructive" : "secondary"}
        aria-live="polite"
      >
        {stateLabel(source.state)}
      </Badge>
      {source.state === "failed" ? (
        <Button
          size="sm"
          variant="outline"
          disabled={retrying}
          onClick={() => onRetry(source)}
          className="motion-safe:active:scale-[0.97] motion-safe:transition-transform"
        >
          {retrying ? "Retrying…" : "Retry"}
        </Button>
      ) : null}
    </li>
  );
}
