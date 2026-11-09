"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { createNote, getNote, updateNote } from "@/lib/api";

/** noteId: undefined = closed, null = new note, string = edit that note. */
interface NoteDialogProps {
  noteId: string | null | undefined;
  onClose: () => void;
  onSaved: () => void;
}

const field =
  "w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

function messageOf(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong.";
}

function Editor({
  noteId,
  onClose,
  onSaved,
}: {
  noteId: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const editing = noteId !== null;
  const [loading, setLoading] = useState(editing);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!noteId) return;
    let cancelled = false;
    getNote(noteId)
      .then((note) => {
        if (cancelled) return;
        setTitle(note.title);
        setContent(note.content);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(messageOf(err));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [noteId]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      if (noteId) await updateNote(noteId, title, content);
      else await createNote(title, content);
      onSaved();
      onClose();
    } catch (err) {
      setError(messageOf(err));
    }
    setSaving(false);
  }

  if (loading) return <p className="text-sm text-muted-foreground">Loading…</p>;

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <label className="block space-y-1 text-sm">
        <span className="font-medium">Title</span>
        <input
          className={field}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <label className="block space-y-1 text-sm">
        <span className="font-medium">Markdown</span>
        <textarea
          className={`${field} min-h-56 font-mono text-xs leading-relaxed`}
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
      </label>
      {error ? (
        <p role="alert" className="text-sm text-red-500 dark:text-red-400">
          {error}
        </p>
      ) : null}
      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          disabled={saving}
          onClick={onClose}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={saving || !title.trim() || !content.trim()}
          className="motion-safe:active:scale-[0.97] motion-safe:transition-transform"
        >
          {saving ? "Saving…" : editing ? "Save changes" : "Add note"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export function NoteDialog({ noteId, onClose, onSaved }: NoteDialogProps) {
  return (
    <Dialog
      open={noteId !== undefined}
      onOpenChange={(open) => !open && onClose()}
    >
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{noteId ? "Edit note" : "New note"}</DialogTitle>
          <DialogDescription>
            Notes are Markdown. They are searchable and citable like any Source.
          </DialogDescription>
        </DialogHeader>
        {noteId !== undefined ? (
          <Editor
            key={noteId ?? "new"}
            noteId={noteId}
            onClose={onClose}
            onSaved={onSaved}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
