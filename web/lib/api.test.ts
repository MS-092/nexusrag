import { describe, expect, test } from "bun:test";
import {
  askBrain,
  createNote,
  deleteSource,
  getNote,
  listSources,
  retrySource,
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
