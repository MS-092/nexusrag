"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  askBrain,
  deleteConversation,
  getConversation,
  listConversations,
  listNotebooks,
  listSkills,
  type ChatResult,
  type ChatScope,
  type ConversationSummary,
  type NotebookSummary,
} from "@/lib/api";
import { scopeToId, turnsFromConversation, type Turn } from "@/lib/chat";
import { matchingSkills, type SkillInfo } from "@/lib/skills";
import { positionLabel } from "@/lib/sources";
import { useSettings } from "@/lib/use-settings";

const press =
  "motion-safe:active:scale-[0.97] motion-safe:transition-transform";

function messageOf(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong.";
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
  const [notebooks, setNotebooks] = useState<NotebookSummary[]>([]);
  const [scopeId, setScopeId] = useState("brain");
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [history, setHistory] = useState<ConversationSummary[]>([]);
  const [historyVersion, setHistoryVersion] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);

  const scope: ChatScope =
    scopeId === "brain" ? { type: "brain" } : { type: "notebook", id: scopeId };

  useEffect(() => {
    let cancelled = false;
    listNotebooks()
      .then((rows) => {
        if (!cancelled) setNotebooks(rows);
      })
      .catch(() => {
        // the switcher just stays on "Whole Brain" if notebooks cannot load
      });
    listSkills()
      .then((rows) => {
        if (!cancelled) setSkills(rows);
      })
      .catch(() => {
        // chat still works without the skill list
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const wanted: ChatScope =
      scopeId === "brain"
        ? { type: "brain" }
        : { type: "notebook", id: scopeId };
    listConversations(wanted)
      .then((rows) => {
        if (!cancelled) setHistory(rows);
      })
      .catch(() => {
        if (!cancelled) setHistory([]);
      });
    return () => {
      cancelled = true;
    };
  }, [scopeId, historyVersion]);

  function newChat() {
    setTurns([]);
    setConversationId(null);
    setNotice(null);
  }

  async function openConversation(id: string) {
    setNotice(null);
    try {
      const conv = await getConversation(id);
      setScopeId(scopeToId(conv.scope));
      setTurns(turnsFromConversation(conv));
      setConversationId(conv.id);
    } catch (err) {
      setNotice(messageOf(err));
    }
  }

  async function removeConversation(id: string) {
    setNotice(null);
    try {
      await deleteConversation(id);
      if (id === conversationId) newChat();
      setHistoryVersion((v) => v + 1);
    } catch (err) {
      setNotice(messageOf(err));
    }
  }

  async function send() {
    const question = text.trim();
    if (!question || pending) return;
    setText("");
    setPending(true);
    setNotice(null);
    setTurns((t) => [...t, { question }]);
    try {
      const result = await askBrain(
        question,
        settings,
        undefined,
        undefined,
        scope,
        conversationId ?? undefined,
      );
      setTurns((t) =>
        t.map((x, i) => (i === t.length - 1 ? { ...x, result } : x)),
      );
      if (result.conversation_id) setConversationId(result.conversation_id);
      setHistoryVersion((v) => v + 1);
    } catch (err) {
      setTurns((t) =>
        t.map((x, i) =>
          i === t.length - 1 ? { ...x, error: messageOf(err) } : x,
        ),
      );
    }
    setPending(false);
  }

  const suggested = matchingSkills(text, skills);

  return (
    <div className="grid gap-8 md:grid-cols-[1fr_14rem]">
      <div className="space-y-6">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Scope</span>
          <select
            aria-label="Chat scope"
            className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={scopeId}
            onChange={(e) => {
              setScopeId(e.target.value);
              newChat();
            }}
          >
            <option value="brain">Whole Brain</option>
            {notebooks.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name}
              </option>
            ))}
          </select>
        </label>

        {turns.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Ask anything about what is in your Brain. Every answer shows where
            it came from.
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
                    {t.result.skill ? (
                      <Badge variant="outline" className="mb-3 mr-2 font-mono">
                        /{t.result.skill}
                      </Badge>
                    ) : null}
                    {t.result.mode === "extractive" ? (
                      <Badge variant="secondary" className="mb-3">
                        Offline answer
                      </Badge>
                    ) : null}
                    <p className="whitespace-pre-wrap">{t.result.answer}</p>
                    <Citations result={t.result} />
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Thinking…</p>
                )}
              </li>
            ))}
          </ol>
        )}

        {notice ? (
          <p role="alert" className="text-sm text-red-500 dark:text-red-400">
            {notice}
          </p>
        ) : null}

        {skills.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-muted-foreground">Skills</span>
            {(suggested.length > 0 ? suggested : skills).map((s) => (
              <button
                key={s.name}
                type="button"
                title={`${s.description} Usage: ${s.usage}`}
                onClick={() => setText(`/${s.name} `)}
                className={`rounded-md bg-muted px-2 py-1 font-mono ${press}`}
              >
                /{s.name}
              </button>
            ))}
          </div>
        ) : null}

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
            className={press}
          >
            {pending ? "Asking…" : "Ask"}
          </Button>
        </form>
      </div>

      <aside aria-labelledby="history-heading" className="space-y-3">
        <div className="flex items-center justify-between">
          <h2
            id="history-heading"
            className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
          >
            History
          </h2>
          <Button size="sm" variant="ghost" onClick={newChat} className={press}>
            New chat
          </Button>
        </div>
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Past conversations in this scope appear here.
          </p>
        ) : (
          <ul className="space-y-1">
            {history.map((c) => (
              <li key={c.id} className="flex items-center gap-1">
                <button
                  type="button"
                  aria-current={c.id === conversationId ? "true" : undefined}
                  onClick={() => void openConversation(c.id)}
                  className={`min-w-0 flex-1 truncate rounded-lg px-3 py-2 text-left text-sm motion-safe:transition-colors ${
                    c.id === conversationId
                      ? "bg-muted font-medium"
                      : "hover:bg-muted/60"
                  }`}
                >
                  {c.title}
                </button>
                <button
                  type="button"
                  aria-label={`Delete conversation ${c.title}`}
                  onClick={() => void removeConversation(c.id)}
                  className="px-2 text-muted-foreground hover:text-foreground"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
    </div>
  );
}
