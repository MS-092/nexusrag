"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ConfirmDeleteProps {
  name: string | null;
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDelete({
  name,
  busy,
  error,
  onCancel,
  onConfirm,
}: ConfirmDeleteProps) {
  return (
    <Dialog
      open={name !== null}
      onOpenChange={(open) => !open && !busy && onCancel()}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete this Source?</DialogTitle>
          <DialogDescription>
            {name} will be removed from your Brain, every Notebook and search.
            This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        {error ? (
          <p role="alert" className="text-sm text-red-500 dark:text-red-400">
            {error}
          </p>
        ) : null}
        <DialogFooter>
          <Button variant="outline" disabled={busy} onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={busy}
            onClick={onConfirm}
            className="motion-safe:active:scale-[0.97] motion-safe:transition-transform"
          >
            {busy ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
