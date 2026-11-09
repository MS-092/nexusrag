export type ProviderChoice =
  "none" | "anthropic" | "openai" | "openai-compatible";

export interface Settings {
  provider: ProviderChoice;
  baseUrl: string;
  model: string;
  key: string;
}

export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export const DEFAULT_SETTINGS: Settings = {
  provider: "none",
  baseUrl: "",
  model: "",
  key: "",
};

const STORAGE_KEY = "nexusrag.provider";

function browserStore(): KeyValueStore | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

const PROVIDERS: ProviderChoice[] = [
  "none",
  "anthropic",
  "openai",
  "openai-compatible",
];

export function loadSettings(
  store: KeyValueStore | null = browserStore(),
): Settings {
  try {
    const raw = store?.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<Settings>;
    if (!parsed.provider || !PROVIDERS.includes(parsed.provider))
      return DEFAULT_SETTINGS;
    return {
      provider: parsed.provider,
      baseUrl: parsed.baseUrl ?? "",
      model: parsed.model ?? "",
      key: parsed.key ?? "",
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(
  settings: Settings,
  store: KeyValueStore | null = browserStore(),
): void {
  try {
    store?.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // storage blocked: keep working for this session only
  }
}

/** The key travels in request headers on each call and is never stored by the API. */
export function providerHeaders(settings: Settings): Record<string, string> {
  if (settings.provider === "none") return {};
  const headers: Record<string, string> = { "X-Provider": settings.provider };
  if (settings.model) headers["X-Provider-Model"] = settings.model;
  if (settings.key) headers["X-Provider-Key"] = settings.key;
  if (settings.baseUrl && settings.provider === "openai-compatible") {
    headers["X-Provider-Base-Url"] = settings.baseUrl;
  }
  return headers;
}
