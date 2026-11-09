"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ACCEPT } from "@/lib/sources";

interface UploadZoneProps {
  busy: boolean;
  onFiles: (files: File[]) => void;
}

export function UploadZone({ busy, onFiles }: UploadZoneProps) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        if (!busy && e.dataTransfer.files.length)
          onFiles([...e.dataTransfer.files]);
      }}
      className={`flex flex-col items-center gap-3 rounded-2xl border border-dashed px-6 py-10 text-center motion-safe:transition-colors motion-safe:duration-150 ${
        over ? "border-primary bg-primary/5" : "border-border"
      }`}
    >
      <p className="text-sm text-muted-foreground">
        Drop files here, or choose them. Accepted:{" "}
        {ACCEPT.split(",").join(", ")}
      </p>
      <Button
        type="button"
        disabled={busy}
        onClick={() => input.current?.click()}
        className="motion-safe:active:scale-[0.97] motion-safe:transition-transform"
      >
        {busy ? "Uploading…" : "Add to Brain"}
      </Button>
      <input
        ref={input}
        type="file"
        multiple
        accept={ACCEPT}
        className="sr-only"
        aria-label="Choose files to add to your Brain"
        onChange={(e) => {
          if (e.target.files?.length) onFiles([...e.target.files]);
          e.target.value = "";
        }}
      />
    </div>
  );
}
