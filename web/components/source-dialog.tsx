"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getSource, type Source } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; source: Source };

interface SourceDialogProps {
  sourceId: string | null;
  onClose: () => void;
}

function SourceBody({ sourceId }: { sourceId: string }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    getSource(sourceId)
      .then((source) => !cancelled && setState({ kind: "ready", source }))
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
  }, [sourceId]);

  if (state.kind === "loading") {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }
  if (state.kind === "error") {
    return (
      <p role="alert" className="text-sm text-red-500 dark:text-red-400">
        {state.message}
      </p>
    );
  }
  return (
    <>
      <p className="truncate text-sm font-medium">{state.source.name}</p>
      {state.source.extracted_text ? (
        <pre className="max-h-[60vh] overflow-auto rounded-lg bg-muted p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap">
          {state.source.extracted_text}
        </pre>
      ) : (
        <p className="text-sm text-muted-foreground">
          No text yet.{" "}
          {state.source.state === "processing" ? "Still processing." : ""}
        </p>
      )}
    </>
  );
}

export function SourceDialog({ sourceId, onClose }: SourceDialogProps) {
  return (
    <Dialog
      open={sourceId !== null}
      onOpenChange={(open) => !open && onClose()}
    >
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Source</DialogTitle>
          <DialogDescription>
            What NexusRAG extracted from this Source.
          </DialogDescription>
        </DialogHeader>
        {sourceId ? <SourceBody key={sourceId} sourceId={sourceId} /> : null}
      </DialogContent>
    </Dialog>
  );
}
