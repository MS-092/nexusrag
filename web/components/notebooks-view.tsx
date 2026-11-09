"use client";

import { useEffect, useState } from "react";
import { ConfirmDelete } from "@/components/confirm-delete";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import {
  createNotebook,
  deleteNotebook,
  getNotebook,
  listNotebooks,
  listSources,
  notebookSources,
  pinSource,
  unpinSource,
  updateNotebook,
  type Notebook,
  type NotebookMember,
  type NotebookSummary,
  type Source,
} from "@/lib/api";
import {
  reasonLabel,
  ruleLabel,
  type Rule,
  type RuleType,
} from "@/lib/notebooks";

const field =
  "rounded-lg border border-border bg-background h-9 px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";
const press =
  "motion-safe:active:scale-[0.97] motion-safe:transition-transform";

function messageOf(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong.";
}

interface Detail {
  notebook: Notebook;
  members: NotebookMember[];
  sources: Source[];
}

function NotebookPanel({
  summary,
  onChanged,
  onDeleted,
}: {
  summary: NotebookSummary;
  onChanged: () => void;
  onDeleted: () => void;
}) {
  const id = summary.id;
  const [version, setVersion] = useState(0);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState(summary.name);
  const [ruleType, setRuleType] = useState<RuleType>("keyword");
  const [ruleValue, setRuleValue] = useState("");
  const [pickSource, setPickSource] = useState("");
  const [confirm, setConfirm] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getNotebook(id), notebookSources(id), listSources()])
      .then(([notebook, members, sources]) => {
        if (!cancelled) setDetail({ notebook, members, sources });
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(messageOf(err));
      });
    return () => {
      cancelled = true;
    };
  }, [id, version]);

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      setVersion((v) => v + 1);
      onChanged();
    } catch (err) {
      setError(messageOf(err));
    }
    setBusy(false);
  }

  if (!detail) {
    return error ? (
      <p role="alert" className="text-sm text-red-500 dark:text-red-400">
        {error}
      </p>
    ) : (
      <p className="text-sm text-muted-foreground">Loading…</p>
    );
  }

  const { notebook, members, sources } = detail;
  const memberIds = new Set(members.map((m) => m.id));
  const pinMode = new Map(notebook.pins.map((p) => [p.source_id, p.mode]));
  const excluded = sources.filter((s) => pinMode.get(s.id) === "out");
  const addable = sources.filter(
    (s) => !memberIds.has(s.id) && pinMode.get(s.id) !== "out",
  );

  function addRule() {
    const value = ruleValue.trim();
    if (!value) return;
    const rules: Rule[] = [...notebook.rules, { type: ruleType, value }];
    setRuleValue("");
    void act(() => updateNotebook(id, { rules }));
  }

  return (
    <div className="space-y-6">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void act(() => updateNotebook(id, { name }));
        }}
      >
        <input
          aria-label="Notebook name"
          className={`${field} flex-1`}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Button
          type="submit"
          variant="outline"
          size="lg"
          disabled={busy || !name.trim() || name === notebook.name}
        >
          Rename
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="lg"
          disabled={busy}
          onClick={() => setConfirm(true)}
        >
          Delete
        </Button>
      </form>

      {error ? (
        <p role="alert" className="text-sm text-red-500 dark:text-red-400">
          {error}
        </p>
      ) : null}

      <section aria-labelledby="rules-heading" className="space-y-2">
        <h3
          id="rules-heading"
          className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
        >
          Rules (a Source matching any rule joins)
        </h3>
        {notebook.rules.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No rules yet. Add one, or pin Sources by hand.
          </p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {notebook.rules.map((r, i) => (
              <li
                key={`${r.type}-${r.value}-${i}`}
                className="flex items-center gap-1 rounded-lg bg-muted px-2 py-1 text-xs"
              >
                {ruleLabel(r)}
                <button
                  type="button"
                  aria-label={`Remove rule ${ruleLabel(r)}`}
                  disabled={busy}
                  className="px-1 text-muted-foreground hover:text-foreground"
                  onClick={() =>
                    void act(() =>
                      updateNotebook(id, {
                        rules: notebook.rules.filter((_, j) => j !== i),
                      }),
                    )
                  }
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            addRule();
          }}
        >
          <Select
            aria-label="Rule type"
            value={ruleType}
            onChange={(e) => setRuleType(e.target.value as RuleType)}
          >
            <option value="keyword">Keyword</option>
            <option value="tag">Tag</option>
            <option value="file_type">File type</option>
          </Select>
          <input
            aria-label="Rule value"
            className={`${field} flex-1`}
            placeholder={
              ruleType === "file_type"
                ? "pdf, image, spreadsheet or note"
                : "value"
            }
            value={ruleValue}
            onChange={(e) => setRuleValue(e.target.value)}
          />
          <Button
            type="submit"
            variant="outline"
            size="lg"
            disabled={busy || !ruleValue.trim()}
            className={press}
          >
            Add rule
          </Button>
        </form>
      </section>

      <section aria-labelledby="members-heading" className="space-y-2">
        <h3
          id="members-heading"
          className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
        >
          Sources in this Notebook ({members.length})
        </h3>
        {members.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing matches yet.</p>
        ) : (
          <ul className="space-y-2">
            {members.map((m) => (
              <li
                key={m.id}
                className="flex items-center gap-3 rounded-xl border border-border px-4 py-2"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{m.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {m.reasons.map(reasonLabel).join(" · ")}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  aria-label={`Remove ${m.name} from this Notebook`}
                  className={press}
                  onClick={() =>
                    void act(() =>
                      pinMode.get(m.id) === "in" && m.reasons.length === 1
                        ? unpinSource(id, m.id)
                        : pinSource(id, m.id, "out"),
                    )
                  }
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {excluded.length > 0 ? (
        <section aria-labelledby="excluded-heading" className="space-y-2">
          <h3
            id="excluded-heading"
            className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
          >
            Pinned out
          </h3>
          <ul className="space-y-2">
            {excluded.map((s) => (
              <li
                key={s.id}
                className="flex items-center gap-3 rounded-xl border border-dashed border-border px-4 py-2"
              >
                <p className="min-w-0 flex-1 truncate text-sm">{s.name}</p>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  className={press}
                  onClick={() => void act(() => unpinSource(id, s.id))}
                >
                  Restore
                </Button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="add-heading" className="space-y-2">
        <h3
          id="add-heading"
          className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
        >
          Pin a Source in
        </h3>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!pickSource) return;
            const chosen = pickSource;
            setPickSource("");
            void act(() => pinSource(id, chosen, "in"));
          }}
        >
          <Select
            aria-label="Source to pin"
            className="flex-1"
            value={pickSource}
            onChange={(e) => setPickSource(e.target.value)}
          >
            <option value="">Choose a Source…</option>
            {addable.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
          <Button
            type="submit"
            variant="outline"
            size="lg"
            disabled={busy || !pickSource}
            className={press}
          >
            Pin in
          </Button>
        </form>
      </section>

      <ConfirmDelete
        name={confirm ? notebook.name : null}
        title="Delete this Notebook?"
        description={`${notebook.name} will be deleted. Its Sources stay in your Brain.`}
        busy={busy}
        error={null}
        onCancel={() => setConfirm(false)}
        onConfirm={() => {
          setConfirm(false);
          void act(async () => {
            await deleteNotebook(id);
            onDeleted();
          });
        }}
      />
    </div>
  );
}

export function NotebooksView() {
  const [notebooks, setNotebooks] = useState<NotebookSummary[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    listNotebooks()
      .then((rows) => {
        if (!cancelled) setNotebooks(rows);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(messageOf(err));
      });
    return () => {
      cancelled = true;
    };
  }, [version]);

  async function create() {
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    setError(null);
    try {
      const nb = await createNotebook(name, []);
      setNewName("");
      setSelected(nb.id);
      setVersion((v) => v + 1);
    } catch (err) {
      setError(messageOf(err));
    }
    setCreating(false);
  }

  const current = notebooks?.find((n) => n.id === selected) ?? null;

  return (
    <div className="grid gap-8 md:grid-cols-[14rem_1fr]">
      <aside className="space-y-3">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void create();
          }}
        >
          <input
            aria-label="New notebook name"
            className={`${field} min-w-0 flex-1`}
            placeholder="New notebook"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <Button
            type="submit"
            variant="outline"
            size="lg"
            disabled={creating || !newName.trim()}
            className={press}
          >
            {creating ? "…" : "Add"}
          </Button>
        </form>
        {error ? (
          <p role="alert" className="text-sm text-red-500 dark:text-red-400">
            {error}
          </p>
        ) : null}
        {notebooks === null && !error ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : null}
        {notebooks?.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No notebooks yet. Create one to focus on part of your Brain.
          </p>
        ) : null}
        <ul className="space-y-1">
          {notebooks?.map((n) => (
            <li key={n.id}>
              <button
                type="button"
                aria-current={n.id === selected ? "true" : undefined}
                onClick={() => setSelected(n.id)}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm motion-safe:transition-colors ${
                  n.id === selected
                    ? "bg-muted font-medium"
                    : "hover:bg-muted/60"
                }`}
              >
                <span className="truncate">{n.name}</span>
                <span className="text-xs text-muted-foreground">
                  {n.member_count}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <section>
        {current ? (
          <NotebookPanel
            key={current.id}
            summary={current}
            onChanged={() => setVersion((v) => v + 1)}
            onDeleted={() => {
              setSelected(null);
              setVersion((v) => v + 1);
            }}
          />
        ) : (
          <p className="text-sm text-muted-foreground">
            Select a Notebook to see what is in it and why.
          </p>
        )}
      </section>
    </div>
  );
}
