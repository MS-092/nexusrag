"use client";

import { useCallback, useEffect, useState } from "react";
import { ConfirmDelete } from "@/components/confirm-delete";
import { NoteDialog } from "@/components/note-dialog";
import { SourceDialog } from "@/components/source-dialog";
import { SourceRow } from "@/components/source-row";
import { Button } from "@/components/ui/button";
import { UploadZone } from "@/components/upload-zone";
import {
  captionSource,
  deleteSource,
  listSources,
  retrySource,
  setPrivate,
  uploadSource,
  type Source,
} from "@/lib/api";
import { hasPending } from "@/lib/sources";
import { useSettings } from "@/lib/use-settings";

const POLL_MS = 1500;

type Load =
  { kind: "loading" } | { kind: "error"; message: string } | { kind: "ready" };

function messageOf(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong.";
}

export function BrainView() {
  const settings = useSettings();
  const [sources, setSources] = useState<Source[]>([]);
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [uploading, setUploading] = useState(false);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [noteId, setNoteId] = useState<string | null | undefined>(undefined);
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

  async function onFiles(files: File[], makePrivate: boolean) {
    setUploading(true);
    setActionError(null);
    const failures: string[] = [];
    for (const file of files) {
      try {
        await uploadSource(file, undefined, undefined, settings, makePrivate);
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

  async function onTogglePrivate(source: Source) {
    setActionError(null);
    try {
      await setPrivate(source.id, !source.private);
    } catch (err) {
      setActionError(`${source.name}: ${messageOf(err)}`);
    }
    await refresh();
  }

  async function onCaption(source: Source) {
    setActionError(null);
    try {
      await captionSource(source.id, settings);
    } catch (err) {
      setActionError(`${source.name}: ${messageOf(err)}`);
    }
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
      <UploadZone busy={uploading} onFiles={(f, p) => void onFiles(f, p)} />
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={() => setNoteId(null)}>
          New note
        </Button>
      </div>
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
                onEdit={(src) => setNoteId(src.id)}
                onTogglePrivate={(src) => void onTogglePrivate(src)}
                canCaption={settings.provider !== "none"}
                onCaption={(src) => void onCaption(src)}
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
      <NoteDialog
        noteId={noteId}
        onClose={() => setNoteId(undefined)}
        onSaved={() => void refresh()}
      />
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
