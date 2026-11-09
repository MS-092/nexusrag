import type { ChatResult, Citation } from "@/lib/api";

export interface SavedMessage {
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  mode: ChatResult["mode"] | null;
  skill: string | null;
  created_at: string;
}

export interface SavedConversation {
  id: string;
  title: string;
  scope: { type: "brain" | "notebook"; id: string | null };
  messages: SavedMessage[];
}

export interface Turn {
  question: string;
  result?: ChatResult;
  error?: string;
}

export function scopeToId(scope: { type: string; id: string | null }): string {
  return scope.type === "notebook" && scope.id ? scope.id : "brain";
}

/** Rebuild chat turns from a saved Conversation: each user message with the assistant reply that follows. */
export function turnsFromConversation(conv: SavedConversation): Turn[] {
  const turns: Turn[] = [];
  for (const m of conv.messages) {
    if (m.role === "user") {
      turns.push({ question: m.content });
    } else if (turns.length > 0) {
      turns[turns.length - 1].result = {
        answer: m.content,
        mode: m.mode ?? "extractive",
        citations: m.citations,
        ...(m.skill ? { skill: m.skill } : {}),
      };
    }
  }
  return turns;
}
