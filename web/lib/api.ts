import { API_URL } from "@/lib/health";
import {
  DEFAULT_SETTINGS,
  providerHeaders,
  type Settings,
} from "@/lib/settings";

export type SourceState = "processing" | "ready" | "failed";
export type SourceKind = "pdf" | "image" | "spreadsheet" | "note";

export interface Source {
  id: string;
  kind: SourceKind;
  name: string;
  size: number;
  state: SourceState;
  error: string | null;
  private: boolean;
  cache_hit: boolean;
  chunk_count: number;
  tags: string[];
  captioned: boolean;
  created_at: string;
  updated_at: string;
  extracted_text?: string;
}

async function request<T>(
  path: string,
  init: RequestInit | undefined,
  baseUrl: string,
  fetcher: typeof fetch,
): Promise<T> {
  let res: Response;
  try {
    res = await fetcher(`${baseUrl}${path}`, init);
  } catch {
    throw new Error(
      "Cannot reach the NexusRAG API. Is it running on this machine?",
    );
  }
  if (!res.ok) {
    let detail = `API returned ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // keep the generic message
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function listSources(baseUrl = API_URL, fetcher: typeof fetch = fetch) {
  return request<Source[]>("/sources", undefined, baseUrl, fetcher);
}

export function getSource(
  id: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Source>(`/sources/${id}`, undefined, baseUrl, fetcher);
}

export function uploadSource(
  file: File,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
  settings: Settings = DEFAULT_SETTINGS,
) {
  const form = new FormData();
  form.append("file", file);
  // Headers (never the body) carry the key so an image can be captioned during ingestion.
  return request<Source>(
    "/sources",
    { method: "POST", body: form, headers: providerHeaders(settings) },
    baseUrl,
    fetcher,
  );
}

export function captionSource(
  id: string,
  settings: Settings,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Source>(
    `/sources/${id}/caption`,
    { method: "POST", headers: providerHeaders(settings) },
    baseUrl,
    fetcher,
  );
}

export function deleteSource(
  id: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<void>(
    `/sources/${id}`,
    { method: "DELETE" },
    baseUrl,
    fetcher,
  );
}

export interface Note {
  id: string;
  title: string;
  content: string;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function createNote(
  title: string,
  content: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Source>(
    "/notes",
    jsonInit("POST", { title, content }),
    baseUrl,
    fetcher,
  );
}

export function updateNote(
  id: string,
  title: string,
  content: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Source>(
    `/notes/${id}`,
    jsonInit("PUT", { title, content }),
    baseUrl,
    fetcher,
  );
}

export function getNote(
  id: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Note>(`/notes/${id}`, undefined, baseUrl, fetcher);
}

export function retrySource(
  id: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Source>(
    `/sources/${id}/retry`,
    { method: "POST" },
    baseUrl,
    fetcher,
  );
}

export interface Citation {
  n: number;
  source_id: string;
  source_name: string;
  kind: SourceKind | null;
  position: { page?: number; sheet?: string; rows?: [number, number] };
  quote: string;
  removed: boolean;
}

export interface ChatResult {
  answer: string;
  mode: "model" | "extractive" | "no_results";
  citations: Citation[];
}

export function askBrain(
  question: string,
  settings: Settings,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<ChatResult>(
    "/chat",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...providerHeaders(settings),
      },
      body: JSON.stringify({ question }),
    },
    baseUrl,
    fetcher,
  );
}
