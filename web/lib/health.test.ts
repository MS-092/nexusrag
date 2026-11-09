import { describe, expect, test } from "bun:test";
import { fetchHealth, summarizeHealth } from "./health";

const okBody = {
  status: "ok",
  embedder: { status: "not_initialized" },
  index: { status: "not_initialized" },
  storage: { status: "ok" },
};

describe("fetchHealth", () => {
  test("returns parsed health from the API", async () => {
    const fetcher = async () =>
      new Response(JSON.stringify(okBody), { status: 200 });
    const result = await fetchHealth(
      "http://api.test",
      fetcher as unknown as typeof fetch,
    );
    expect(result.status).toBe("ok");
    expect(result.storage.status).toBe("ok");
  });

  test("throws a readable error when the API answers with an error", async () => {
    const fetcher = async () => new Response("nope", { status: 500 });
    await expect(
      fetchHealth("http://api.test", fetcher as unknown as typeof fetch),
    ).rejects.toThrow("API returned 500");
  });

  test("throws a readable error when the API is unreachable", async () => {
    const fetcher = async () => {
      throw new TypeError("fetch failed");
    };
    await expect(
      fetchHealth("http://api.test", fetcher as unknown as typeof fetch),
    ).rejects.toThrow("Cannot reach the NexusRAG API");
  });
});

describe("summarizeHealth", () => {
  test("lists each component with its status", () => {
    const rows = summarizeHealth(okBody);
    expect(rows).toEqual([
      { name: "Storage", status: "ok" },
      { name: "Embedder", status: "not_initialized" },
      { name: "Index", status: "not_initialized" },
    ]);
  });
});
