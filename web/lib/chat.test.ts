import { describe, expect, test } from "bun:test";
import {
  scopeToId,
  turnsFromConversation,
  type SavedConversation,
} from "./chat";

const conv: SavedConversation = {
  id: "c1",
  title: "Revenue?",
  scope: { type: "notebook", id: "n1" },
  messages: [
    {
      role: "user",
      content: "What was revenue?",
      citations: [],
      mode: null,
      skill: null,
      created_at: "t",
    },
    {
      role: "assistant",
      content: "4.2 million [1]",
      citations: [
        {
          n: 1,
          source_id: "s1",
          source_name: "finance.pdf",
          kind: "pdf",
          position: { page: 1 },
          quote: "Revenue in Q3 was 4.2 million",
          removed: true,
        },
      ],
      mode: "model",
      skill: null,
      created_at: "t",
    },
    {
      role: "user",
      content: "And headcount?",
      citations: [],
      mode: null,
      skill: null,
      created_at: "t",
    },
  ],
};

describe("turnsFromConversation", () => {
  test("pairs questions with their answers and keeps citations and removed flags", () => {
    const turns = turnsFromConversation(conv);
    expect(turns).toHaveLength(2);
    expect(turns[0].question).toBe("What was revenue?");
    expect(turns[0].result?.answer).toBe("4.2 million [1]");
    expect(turns[0].result?.citations[0].removed).toBe(true);
  });

  test("a trailing unanswered question has no result yet", () => {
    expect(turnsFromConversation(conv)[1]).toEqual({
      question: "And headcount?",
    });
  });
});

describe("scopeToId", () => {
  test("maps scopes to the switcher value", () => {
    expect(scopeToId({ type: "brain", id: null })).toBe("brain");
    expect(scopeToId({ type: "notebook", id: "n1" })).toBe("n1");
  });
});
