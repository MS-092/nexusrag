import { describe, expect, test } from "bun:test";
import {
  DEFAULT_SETTINGS,
  loadSettings,
  providerHeaders,
  saveSettings,
  type KeyValueStore,
} from "./settings";

function memoryStore(
  initial: Record<string, string> = {},
): KeyValueStore & { data: Record<string, string> } {
  const data = { ...initial };
  return {
    data,
    getItem: (k) => data[k] ?? null,
    setItem: (k, v) => {
      data[k] = v;
    },
    removeItem: (k) => {
      delete data[k];
    },
  };
}

describe("settings", () => {
  test("defaults to no provider (offline extractive answers)", () => {
    expect(loadSettings(memoryStore())).toEqual(DEFAULT_SETTINGS);
    expect(DEFAULT_SETTINGS.provider).toBe("none");
  });

  test("round-trips through the store", () => {
    const store = memoryStore();
    const s = {
      provider: "anthropic" as const,
      baseUrl: "",
      model: "claude-x",
      key: "sk-ant-1",
    };
    saveSettings(s, store);
    expect(loadSettings(store)).toEqual(s);
  });

  test("survives corrupt or unavailable storage", () => {
    expect(
      loadSettings(memoryStore({ "nexusrag.provider": "{{not json" })),
    ).toEqual(DEFAULT_SETTINGS);
    const broken: KeyValueStore = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
      removeItem: () => {},
    };
    expect(loadSettings(broken)).toEqual(DEFAULT_SETTINGS);
    expect(() => saveSettings(DEFAULT_SETTINGS, broken)).not.toThrow();
  });
});

describe("providerHeaders", () => {
  test("sends nothing when no provider is chosen", () => {
    expect(providerHeaders(DEFAULT_SETTINGS)).toEqual({});
  });

  test("sends provider, model and key per request", () => {
    expect(
      providerHeaders({
        provider: "openai",
        baseUrl: "",
        model: "gpt-x",
        key: "sk-1",
      }),
    ).toEqual({
      "X-Provider": "openai",
      "X-Provider-Model": "gpt-x",
      "X-Provider-Key": "sk-1",
    });
  });

  test("includes the base URL for openai-compatible and omits blanks", () => {
    expect(
      providerHeaders({
        provider: "openai-compatible",
        baseUrl: "http://localhost:11434",
        model: "llama3",
        key: "",
      }),
    ).toEqual({
      "X-Provider": "openai-compatible",
      "X-Provider-Model": "llama3",
      "X-Provider-Base-Url": "http://localhost:11434",
    });
  });
});
