import { describe, expect, test } from "bun:test";
import {
  askBrain,
  listSources,
  retrySource,
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
