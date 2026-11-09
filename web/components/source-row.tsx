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
  onDelete: (source: Source) => void;
  onEdit: (source: Source) => void;
  onCaption: (source: Source) => void;
  canCaption: boolean;
}

export function SourceRow({
  source,
  retrying,
  onOpen,
  onRetry,
  onDelete,
  onEdit,
  onCaption,
  canCaption,
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
          {source.captioned ? " · captioned" : ""}
        </span>
        {source.tags.length > 0 ? (
          <span className="mt-1 flex flex-wrap gap-1">
            {source.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-md bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
              >
                #{tag}
              </span>
            ))}
          </span>
        ) : null}
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
      {source.kind === "image" &&
      source.state === "ready" &&
      !source.captioned ? (
        <Button
          size="sm"
          variant="outline"
          disabled={!canCaption}
          title={
            canCaption
              ? undefined
              : "Choose a provider in Settings to caption images"
          }
          onClick={() => onCaption(source)}
          className="motion-safe:active:scale-[0.97] motion-safe:transition-transform"
        >
          Add caption
        </Button>
      ) : null}
      {source.kind === "note" ? (
        <Button
          size="sm"
          variant="ghost"
          aria-label={`Edit ${source.name}`}
          onClick={() => onEdit(source)}
          className="motion-safe:active:scale-[0.97] motion-safe:transition-transform"
        >
          Edit
        </Button>
      ) : null}
      <Button
        size="sm"
        variant="ghost"
        aria-label={`Delete ${source.name}`}
        onClick={() => onDelete(source)}
        className="motion-safe:active:scale-[0.97] motion-safe:transition-transform"
      >
        Delete
      </Button>
    </li>
  );
}
