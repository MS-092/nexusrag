"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { askBrain, type ChatResult } from "@/lib/api";
import { positionLabel } from "@/lib/sources";
import { useSettings } from "@/lib/use-settings";

interface Turn {
  question: string;
  result?: ChatResult;
  error?: string;
}

function Citations({ result }: { result: ChatResult }) {
  if (!result.citations.length) return null;
  return (
    <ul className="mt-3 space-y-2">
      {result.citations.map((c) => (
        <li key={c.n}>
          <details className="group rounded-lg border border-border px-3 py-2 text-xs">
            <summary className="cursor-pointer list-none">
              <span className="font-medium">[{c.n}]</span> {c.source_name}
              {positionLabel(c.position)
                ? ` · ${positionLabel(c.position)}`
                : ""}
              {c.removed ? " · removed" : ""}
            </summary>
            <p className="mt-2 whitespace-pre-wrap text-muted-foreground">
              {c.quote}
            </p>
          </details>
        </li>
      ))}
    </ul>
  );
}

export function ChatView() {
  const settings = useSettings();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);

  async function send() {
    const question = text.trim();
    if (!question || pending) return;
    setText("");
    setPending(true);
    setTurns((t) => [...t, { question }]);
    try {
      const result = await askBrain(question, settings);
      setTurns((t) =>
        t.map((x, i) => (i === t.length - 1 ? { ...x, result } : x)),
      );
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";
      setTurns((t) =>
        t.map((x, i) => (i === t.length - 1 ? { ...x, error: message } : x)),
      );
    }
    setPending(false);
  }

  return (
    <div className="space-y-6">
      {turns.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Ask anything about what is in your Brain. Every answer shows where it
          came from.
        </p>
      ) : (
        <ol className="space-y-6">
          {turns.map((t, i) => (
            <li key={i} className="space-y-2">
              <p className="text-sm font-medium">{t.question}</p>
              {t.error ? (
                <p
                  role="alert"
                  className="text-sm text-red-500 dark:text-red-400"
                >
                  {t.error}
                </p>
              ) : t.result ? (
                <div className="rounded-xl border border-border p-4 text-sm">
                  <p className="whitespace-pre-wrap">{t.result.answer}</p>
                  {t.result.mode === "extractive" ? (
                    <Badge variant="secondary" className="mt-3">
                      Offline answer
                    </Badge>
                  ) : null}
                  <Citations result={t.result} />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Thinking…</p>
              )}
            </li>
          ))}
        </ol>
      )}
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          aria-label="Ask your Brain"
          className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder="Ask your Brain…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Button
          type="submit"
          disabled={pending || !text.trim()}
          className="motion-safe:active:scale-[0.97] motion-safe:transition-transform"
        >
          {pending ? "Asking…" : "Ask"}
        </Button>
      </form>
    </div>
  );
}
