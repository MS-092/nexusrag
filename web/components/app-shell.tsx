"use client";

import { useState } from "react";
import { ActivityView } from "@/components/activity-view";
import { BrainView } from "@/components/brain-view";
import { ChatView } from "@/components/chat-view";
import { NotebooksView } from "@/components/notebooks-view";
import { SettingsDialog } from "@/components/settings-dialog";

type Tab = "sources" | "notebooks" | "chat" | "activity";

const TABS: { id: Tab; label: string }[] = [
  { id: "sources", label: "Sources" },
  { id: "notebooks", label: "Notebooks" },
  { id: "chat", label: "Chat" },
  { id: "activity", label: "Activity" },
];

export function AppShell() {
  const [tab, setTab] = useState<Tab>("sources");
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <nav
          aria-label="Sections"
          className="flex gap-1 rounded-xl bg-muted p-1"
        >
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              aria-current={tab === t.id ? "page" : undefined}
              onClick={() => setTab(t.id)}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium motion-safe:transition-colors motion-safe:active:scale-[0.97] ${
                tab === t.id
                  ? "bg-background shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <SettingsDialog />
      </div>
      {tab === "sources" ? (
        <BrainView />
      ) : tab === "notebooks" ? (
        <NotebooksView />
      ) : tab === "activity" ? (
        <ActivityView />
      ) : (
        <ChatView />
      )}
    </div>
  );
}
