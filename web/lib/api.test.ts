import { describe, expect, test } from "bun:test";
import {
  askBrain,
  captionSource,
  createNotebook,
  createNote,
  deleteConversation,
  deleteNotebook,
  deleteSource,
  getConversation,
  getNote,
  listActivity,
  listConversations,
  listNotebooks,
  listSkills,
  listSources,
  pinSource,
  retrySource,
  setPrivate,
  unpinSource,
  updateNote,
  uploadSource,
  type Source,
} from "./api";
import { DEFAULT_SETTINGS } from "./settings";

const source: Source = {
  id: "s1",
  kind: "pdf",
  name: "report.pdf",
  size: 10,
  state: "processing",
  error: null,
  private: false,
  cache_hit: false,
  chunk_count: 0,
  tags: [],
  captioned: false,
  created_at: "2026-11-08T00:00:00Z",
  updated_at: "2026-11-08T00:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

describe("api client", () => {
  test("listSources returns the sources", async () => {
    const f = (async () => json([source])) as unknown as typeof fetch;
    expect(await listSources("http://api.test", f)).toEqual([source]);
  });

  test("uploadSource posts multipart form data", async () => {
    const seen: { url?: string; method?: string; isForm?: boolean } = {};
    const f = (async (url: string, init?: RequestInit) => {
      seen.url = url;
      seen.method = init?.method;
      seen.isForm = init?.body instanceof FormData;
      return json(source, 202);
    }) as unknown as typeof fetch;
    const file = new File(["x"], "report.pdf", { type: "application/pdf" });
    const result = await uploadSource(file, "http://api.test", f);
    expect(result.state).toBe("processing");
    expect(seen).toEqual({
      url: "http://api.test/sources",
      method: "POST",
      isForm: true,
    });
  });

  test("surfaces the server's detail message on rejection", async () => {
    const f = (async () =>
      json(
        { detail: "File is over the 50 MB limit." },
        413,
      )) as unknown as typeof fetch;
    const file = new File(["x"], "big.pdf");
    await expect(uploadSource(file, "http://api.test", f)).rejects.toThrow(
      "File is over the 50 MB limit.",
    );
  });

  test("retrySource posts to the retry endpoint", async () => {
    let url = "";
    const f = (async (u: string) => {
      url = u;
      return json(source, 202);
    }) as unknown as typeof fetch;
    await retrySource("s1", "http://api.test", f);
    expect(url).toBe("http://api.test/sources/s1/retry");
  });

  test("falls back to a readable message when the API is unreachable", async () => {
    const f = (async () => {
      throw new TypeError("fetch failed");
    }) as unknown as typeof fetch;
    await expect(listSources("http://api.test", f)).rejects.toThrow(
      "Cannot reach the NexusRAG API",
    );
  });
});

describe("askBrain", () => {
  const reply = {
    answer: "Revenue was 4.2 million [1].",
    mode: "model",
    citations: [
      {
        n: 1,
        source_id: "s1",
        source_name: "finance.pdf",
        kind: "pdf",
        position: { page: 1 },
        quote: "Revenue in Q3 was 4.2 million",
        removed: false,
      },
    ],
  };

  test("posts the question with provider headers and returns citations", async () => {
    const seen: { headers?: Record<string, string>; body?: string } = {};
    const f = (async (_u: string, init?: RequestInit) => {
      seen.headers = init?.headers as Record<string, string>;
      seen.body = init?.body as string;
      return json(reply);
    }) as unknown as typeof fetch;
    const result = await askBrain(
      "What was revenue?",
      { provider: "openai", baseUrl: "", model: "gpt-x", key: "sk-1" },
      "http://api.test",
      f,
    );
    expect(result.citations[0].source_name).toBe("finance.pdf");
    expect(JSON.parse(seen.body ?? "{}")).toEqual({
      question: "What was revenue?",
    });
    expect(seen.headers?.["X-Provider-Key"]).toBe("sk-1");
    expect(seen.headers?.["Content-Type"]).toBe("application/json");
  });

  test("sends no provider headers when offline", async () => {
    const seen: { headers?: Record<string, string> } = {};
    const f = (async (_u: string, init?: RequestInit) => {
      seen.headers = init?.headers as Record<string, string>;
      return json({ ...reply, mode: "extractive" });
    }) as unknown as typeof fetch;
    await askBrain("q", DEFAULT_SETTINGS, "http://api.test", f);
    expect(Object.keys(seen.headers ?? {})).toEqual(["Content-Type"]);
  });

  test("surfaces a provider error message", async () => {
    const f = (async () =>
      json(
        { detail: "The provider rejected the API key." },
        401,
      )) as unknown as typeof fetch;
    await expect(
      askBrain("q", DEFAULT_SETTINGS, "http://api.test", f),
    ).rejects.toThrow("The provider rejected the API key.");
  });
});

describe("deleteSource", () => {
  test("sends DELETE and tolerates the empty 204 response", async () => {
    const seen: { url?: string; method?: string } = {};
    const f = (async (u: string, init?: RequestInit) => {
      seen.url = u;
      seen.method = init?.method;
      return new Response(null, { status: 204 });
    }) as unknown as typeof fetch;
    await deleteSource("s1", "http://api.test", f);
    expect(seen).toEqual({
      url: "http://api.test/sources/s1",
      method: "DELETE",
    });
  });

  test("reports a missing source", async () => {
    const f = (async () =>
      json({ detail: "Source not found" }, 404)) as unknown as typeof fetch;
    await expect(deleteSource("nope", "http://api.test", f)).rejects.toThrow(
      "Source not found",
    );
  });
});

describe("notes", () => {
  test("createNote posts title and content as JSON", async () => {
    const seen: { url?: string; method?: string; body?: string } = {};
    const f = (async (u: string, init?: RequestInit) => {
      seen.url = u;
      seen.method = init?.method;
      seen.body = init?.body as string;
      return json({ ...source, kind: "note", name: "Plan" }, 202);
    }) as unknown as typeof fetch;
    const result = await createNote("Plan", "# Plan", "http://api.test", f);
    expect(result.kind).toBe("note");
    expect(seen.url).toBe("http://api.test/notes");
    expect(seen.method).toBe("POST");
    expect(JSON.parse(seen.body ?? "{}")).toEqual({
      title: "Plan",
      content: "# Plan",
    });
  });

  test("updateNote puts to the note endpoint", async () => {
    const seen: { url?: string; method?: string } = {};
    const f = (async (u: string, init?: RequestInit) => {
      seen.url = u;
      seen.method = init?.method;
      return json(source, 202);
    }) as unknown as typeof fetch;
    await updateNote("n1", "Plan", "x", "http://api.test", f);
    expect(seen).toEqual({ url: "http://api.test/notes/n1", method: "PUT" });
  });

  test("getNote returns the raw markdown", async () => {
    const f = (async () =>
      json({
        id: "n1",
        title: "Plan",
        content: "# Plan",
      })) as unknown as typeof fetch;
    expect(await getNote("n1", "http://api.test", f)).toEqual({
      id: "n1",
      title: "Plan",
      content: "# Plan",
    });
  });

  test("validation errors from the API are readable", async () => {
    const f = (async () =>
      json({ detail: "Note not found" }, 404)) as unknown as typeof fetch;
    await expect(
      updateNote("x", "t", "c", "http://api.test", f),
    ).rejects.toThrow("Note not found");
  });
});

describe("captions and provider headers on upload", () => {
  const withKey = {
    provider: "openai" as const,
    baseUrl: "",
    model: "gpt-x",
    key: "sk-1",
  };

  test("uploadSource forwards provider headers so images can be captioned", async () => {
    const seen: { headers?: Record<string, string> } = {};
    const f = (async (_u: string, init?: RequestInit) => {
      seen.headers = init?.headers as Record<string, string>;
      return json(source, 202);
    }) as unknown as typeof fetch;
    await uploadSource(new File(["x"], "a.png"), "http://api.test", f, withKey);
    expect(seen.headers?.["X-Provider-Key"]).toBe("sk-1");
  });

  test("uploadSource sends no provider headers by default", async () => {
    const seen: { headers?: unknown } = {};
    const f = (async (_u: string, init?: RequestInit) => {
      seen.headers = init?.headers;
      return json(source, 202);
    }) as unknown as typeof fetch;
    await uploadSource(new File(["x"], "a.png"), "http://api.test", f);
    expect(seen.headers).toEqual({});
  });

  test("captionSource posts to the caption endpoint with provider headers", async () => {
    const seen: {
      url?: string;
      method?: string;
      headers?: Record<string, string>;
    } = {};
    const f = (async (u: string, init?: RequestInit) => {
      seen.url = u;
      seen.method = init?.method;
      seen.headers = init?.headers as Record<string, string>;
      return json(source, 202);
    }) as unknown as typeof fetch;
    await captionSource("s1", withKey, "http://api.test", f);
    expect(seen.url).toBe("http://api.test/sources/s1/caption");
    expect(seen.method).toBe("POST");
    expect(seen.headers?.["X-Provider"]).toBe("openai");
  });
});

describe("private sources", () => {
  test("uploadSource can mark the new source private", async () => {
    let url = "";
    const f = (async (u: string) => {
      url = u;
      return json(source, 202);
    }) as unknown as typeof fetch;
    await uploadSource(
      new File(["x"], "a.png"),
      "http://api.test",
      f,
      DEFAULT_SETTINGS,
      true,
    );
    expect(url).toBe("http://api.test/sources?private=true");
  });

  test("uploadSource is public by default", async () => {
    let url = "";
    const f = (async (u: string) => {
      url = u;
      return json(source, 202);
    }) as unknown as typeof fetch;
    await uploadSource(new File(["x"], "a.png"), "http://api.test", f);
    expect(url).toBe("http://api.test/sources");
  });

  test("setPrivate patches the source", async () => {
    const seen: { url?: string; method?: string; body?: string } = {};
    const f = (async (u: string, init?: RequestInit) => {
      seen.url = u;
      seen.method = init?.method;
      seen.body = init?.body as string;
      return json({ ...source, private: true });
    }) as unknown as typeof fetch;
    const result = await setPrivate("s1", true, "http://api.test", f);
    expect(result.private).toBe(true);
    expect(seen.url).toBe("http://api.test/sources/s1");
    expect(seen.method).toBe("PATCH");
    expect(JSON.parse(seen.body ?? "{}")).toEqual({ private: true });
  });
});

describe("notebooks", () => {
  const nb = { id: "n1", name: "Finance", rules: [], member_count: 0 };

  test("createNotebook posts name and rules", async () => {
    const seen: { url?: string; method?: string; body?: string } = {};
    const f = (async (u: string, init?: RequestInit) => {
      seen.url = u;
      seen.method = init?.method;
      seen.body = init?.body as string;
      return json({ id: "n1", name: "Finance", rules: [], pins: [] }, 201);
    }) as unknown as typeof fetch;
    await createNotebook(
      "Finance",
      [{ type: "tag", value: "billing" }],
      "http://api.test",
      f,
    );
    expect(seen.url).toBe("http://api.test/notebooks");
    expect(seen.method).toBe("POST");
    expect(JSON.parse(seen.body ?? "{}")).toEqual({
      name: "Finance",
      rules: [{ type: "tag", value: "billing" }],
    });
  });

  test("listNotebooks returns member counts", async () => {
    const f = (async () => json([nb])) as unknown as typeof fetch;
    expect(await listNotebooks("http://api.test", f)).toEqual([nb]);
  });

  test("pinSource puts a pin mode and unpinSource deletes it", async () => {
    const calls: { url: string; method?: string; body?: string }[] = [];
    const f = (async (u: string, init?: RequestInit) => {
      calls.push({ url: u, method: init?.method, body: init?.body as string });
      return init?.method === "DELETE"
        ? new Response(null, { status: 204 })
        : json({ notebook_id: "n1", source_id: "s1", mode: "out" });
    }) as unknown as typeof fetch;
    await pinSource("n1", "s1", "out", "http://api.test", f);
    await unpinSource("n1", "s1", "http://api.test", f);
    expect(calls[0]).toEqual({
      url: "http://api.test/notebooks/n1/pins/s1",
      method: "PUT",
      body: JSON.stringify({ mode: "out" }),
    });
    expect(calls[1].url).toBe("http://api.test/notebooks/n1/pins/s1");
    expect(calls[1].method).toBe("DELETE");
  });

  test("deleteNotebook tolerates 204", async () => {
    const f = (async () =>
      new Response(null, { status: 204 })) as unknown as typeof fetch;
    await expect(
      deleteNotebook("n1", "http://api.test", f),
    ).resolves.toBeUndefined();
  });
});

describe("chat scope", () => {
  const reply = { answer: "x", mode: "extractive", citations: [] };

  test("askBrain sends the notebook scope when given", async () => {
    let body = "";
    const f = (async (_u: string, init?: RequestInit) => {
      body = init?.body as string;
      return json(reply);
    }) as unknown as typeof fetch;
    await askBrain("q", DEFAULT_SETTINGS, "http://api.test", f, {
      type: "notebook",
      id: "n1",
    });
    expect(JSON.parse(body)).toEqual({
      question: "q",
      scope: { type: "notebook", id: "n1" },
    });
  });

  test("askBrain omits the scope for the whole Brain", async () => {
    let body = "";
    const f = (async (_u: string, init?: RequestInit) => {
      body = init?.body as string;
      return json(reply);
    }) as unknown as typeof fetch;
    await askBrain("q", DEFAULT_SETTINGS, "http://api.test", f);
    expect(JSON.parse(body)).toEqual({ question: "q" });
  });
});

describe("activity", () => {
  test("listActivity filters by notebook", async () => {
    let url = "";
    const f = (async (u: string) => {
      url = u;
      return json([]);
    }) as unknown as typeof fetch;
    await listActivity("n1", "http://api.test", f);
    expect(url).toBe("http://api.test/activity?notebook_id=n1");
    await listActivity(undefined, "http://api.test", f);
    expect(url).toBe("http://api.test/activity");
  });
});

describe("skills", () => {
  test("listSkills returns name, description and usage", async () => {
    const skills = [
      { name: "summarize", description: "Summarize.", usage: "/summarize [x]" },
    ];
    let url = "";
    const f = (async (u: string) => {
      url = u;
      return json(skills);
    }) as unknown as typeof fetch;
    expect(await listSkills("http://api.test", f)).toEqual(skills);
    expect(url).toBe("http://api.test/skills");
  });
});

describe("conversations", () => {
  test("listConversations filters by scope", async () => {
    const urls: string[] = [];
    const f = (async (u: string) => {
      urls.push(u);
      return json([]);
    }) as unknown as typeof fetch;
    await listConversations({ type: "brain" }, "http://api.test", f);
    await listConversations(
      { type: "notebook", id: "n1" },
      "http://api.test",
      f,
    );
    expect(urls).toEqual([
      "http://api.test/conversations?scope=brain",
      "http://api.test/conversations?scope=notebook&notebook_id=n1",
    ]);
  });

  test("getConversation and deleteConversation use the conversation endpoint", async () => {
    const calls: { url: string; method?: string }[] = [];
    const f = (async (u: string, init?: RequestInit) => {
      calls.push({ url: u, method: init?.method });
      return init?.method === "DELETE"
        ? new Response(null, { status: 204 })
        : json({
            id: "c1",
            title: "t",
            scope: { type: "brain", id: null },
            messages: [],
          });
    }) as unknown as typeof fetch;
    await getConversation("c1", "http://api.test", f);
    await deleteConversation("c1", "http://api.test", f);
    expect(calls).toEqual([
      { url: "http://api.test/conversations/c1", method: undefined },
      { url: "http://api.test/conversations/c1", method: "DELETE" },
    ]);
  });

  test("askBrain sends the conversation id for follow-ups", async () => {
    let body = "";
    const f = (async (_u: string, init?: RequestInit) => {
      body = init?.body as string;
      return json({
        answer: "x",
        mode: "extractive",
        citations: [],
        conversation_id: "c1",
      });
    }) as unknown as typeof fetch;
    await askBrain(
      "q",
      DEFAULT_SETTINGS,
      "http://api.test",
      f,
      undefined,
      "c1",
    );
    expect(JSON.parse(body)).toEqual({ question: "q", conversation_id: "c1" });
  });
});
