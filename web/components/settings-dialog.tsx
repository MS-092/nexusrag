"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { ProviderChoice, Settings } from "@/lib/settings";
import { updateSettings, useSettings } from "@/lib/use-settings";

const LABELS: Record<ProviderChoice, string> = {
  none: "None (offline answers from your Sources)",
  anthropic: "Anthropic",
  openai: "OpenAI",
  "openai-compatible": "OpenAI-compatible (Ollama, OpenRouter, OpenCode…)",
};

const field =
  "w-full rounded-lg border border-border bg-background h-9 px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

function Form({ initial, onDone }: { initial: Settings; onDone: () => void }) {
  const [draft, setDraft] = useState<Settings>(initial);
  const set = <K extends keyof Settings>(k: K, v: Settings[K]) =>
    setDraft((d) => ({ ...d, [k]: v }));
  const usesKey = draft.provider === "anthropic" || draft.provider === "openai";

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        updateSettings(draft);
        onDone();
      }}
    >
      <label className="block space-y-1 text-sm">
        <span className="font-medium">Provider</span>
        <Select
          className="w-full"
          value={draft.provider}
          onChange={(e) => set("provider", e.target.value as ProviderChoice)}
        >
          {(Object.keys(LABELS) as ProviderChoice[]).map((p) => (
            <option key={p} value={p}>
              {LABELS[p]}
            </option>
          ))}
        </Select>
      </label>
      {draft.provider === "openai-compatible" ? (
        <label className="block space-y-1 text-sm">
          <span className="font-medium">Base URL</span>
          <input
            className={field}
            placeholder="http://localhost:11434"
            value={draft.baseUrl}
            onChange={(e) => set("baseUrl", e.target.value)}
          />
        </label>
      ) : null}
      {draft.provider !== "none" ? (
        <>
          <label className="block space-y-1 text-sm">
            <span className="font-medium">
              Model{" "}
              {usesKey
                ? "(optional, a sensible default is used)"
                : "(required)"}
            </span>
            <input
              className={field}
              value={draft.model}
              onChange={(e) => set("model", e.target.value)}
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-medium">
              API key {usesKey ? "" : "(optional for local models)"}
            </span>
            <input
              type="password"
              autoComplete="off"
              className={field}
              value={draft.key}
              onChange={(e) => set("key", e.target.value)}
            />
          </label>
        </>
      ) : null}
      <p className="rounded-lg bg-muted p-3 text-xs leading-relaxed text-muted-foreground">
        Your key is kept in this browser&apos;s localStorage and sent with each
        request. Anything that can run script on this page can read it.
        NexusRAG&apos;s server never stores or logs it.
      </p>
      <Button
        type="submit"
        className="motion-safe:active:scale-[0.97] motion-safe:transition-transform"
      >
        Save
      </Button>
    </form>
  );
}

export function SettingsDialog() {
  const settings = useSettings();
  const [open, setOpen] = useState(false);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" size="sm" />}>
        Settings
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>AI provider</DialogTitle>
          <DialogDescription>
            Bring your own key. Leave the provider on None to stay fully
            offline.
          </DialogDescription>
        </DialogHeader>
        {open ? (
          <Form initial={settings} onDone={() => setOpen(false)} />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
