"use client";

import { useCallback, useEffect, useState } from "react";
import { ConfirmDelete } from "@/components/confirm-delete";
import { SourceDialog } from "@/components/source-dialog";
import { SourceRow } from "@/components/source-row";
import { UploadZone } from "@/components/upload-zone";
import {
  deleteSource,
  listSources,
  retrySource,
  uploadSource,
  type Source,
} from "@/lib/api";
import { hasPending } from "@/lib/sources";

const POLL_MS = 1500;

type Load =
  { kind: "loading" } | { kind: "error"; message: string } | { kind: "ready" };

function messageOf(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong.";
}

export function BrainView() {
  const [sources, setSources] = useState<Source[]>([]);
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [uploading, setUploading] = useState(false);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Source | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setSources(await listSources());
      setLoad({ kind: "ready" });
    } catch (err) {
      setLoad({ kind: "error", message: messageOf(err) });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    listSources()
      .then((rows) => {
        if (cancelled) return;
        setSources(rows);
        setLoad({ kind: "ready" });
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoad({ kind: "error", message: messageOf(err) });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const pending = hasPending(sources);
  useEffect(() => {
    if (!pending) return;
    const id = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(id);
  }, [pending, refresh]);

  async function onFiles(files: File[]) {
    setUploading(true);
    setActionError(null);
    const failures: string[] = [];
    for (const file of files) {
      try {
        await uploadSource(file);
      } catch (err) {
        failures.push(`${file.name}: ${messageOf(err)}`);
      }
    }
    if (failures.length) setActionError(failures.join(" "));
    setUploading(false);
    await refresh();
  }

  async function onRetry(source: Source) {
    setRetrying(source.id);
    setActionError(null);
    try {
      await retrySource(source.id);
    } catch (err) {
      setActionError(`${source.name}: ${messageOf(err)}`);
    }
    setRetrying(null);
    await refresh();
  }

  async function onConfirmDelete() {
    if (!toDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteSource(toDelete.id);
      setToDelete(null);
      await refresh();
    } catch (err) {
      setDeleteError(messageOf(err));
    }
    setDeleting(false);
  }

  return (
    <div className="space-y-6">
      <UploadZone busy={uploading} onFiles={(f) => void onFiles(f)} />
      {actionError ? (
        <p role="alert" className="text-sm text-red-500 dark:text-red-400">
          {actionError}
        </p>
      ) : null}
      <section aria-labelledby="sources-heading" className="space-y-3">
        <h2
          id="sources-heading"
          className="text-sm font-medium tracking-wide text-muted-foreground uppercase"
        >
          Sources
        </h2>
        {load.kind === "loading" ? (
          <p className="text-sm text-muted-foreground">Loading your Brain…</p>
        ) : null}
        {load.kind === "error" ? (
          <p role="alert" className="text-sm text-red-500 dark:text-red-400">
            {load.message}
          </p>
        ) : null}
        {load.kind === "ready" && sources.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Your Brain is empty. Add a PDF, spreadsheet or image to get started.
          </p>
        ) : null}
        {sources.length > 0 ? (
          <ul className="space-y-2">
            {sources.map((s) => (
              <SourceRow
                key={s.id}
                source={s}
                retrying={retrying === s.id}
                onOpen={(src) => setOpen(src.id)}
                onRetry={(src) => void onRetry(src)}
                onDelete={(src) => {
                  setDeleteError(null);
                  setToDelete(src);
                }}
              />
            ))}
          </ul>
        ) : null}
      </section>
      <SourceDialog sourceId={open} onClose={() => setOpen(null)} />
      <ConfirmDelete
        name={toDelete?.name ?? null}
        busy={deleting}
        error={deleteError}
        onCancel={() => setToDelete(null)}
        onConfirm={() => void onConfirmDelete()}
      />
    </div>
  );
}
