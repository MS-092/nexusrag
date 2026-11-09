import { API_URL } from "@/lib/health";
import type { SkillInfo } from "@/lib/skills";
import type { ActivityEvent } from "@/lib/activity";
import type { Reason, Rule } from "@/lib/notebooks";
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
  makePrivate = false,
) {
  const form = new FormData();
  form.append("file", file);
  // Headers (never the body) carry the key so an image can be captioned during ingestion.
  // A private upload is never captioned or sent to any provider.
  return request<Source>(
    `/sources${makePrivate ? "?private=true" : ""}`,
    { method: "POST", body: form, headers: providerHeaders(settings) },
    baseUrl,
    fetcher,
  );
}

export function setPrivate(
  id: string,
  value: boolean,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Source>(
    `/sources/${id}`,
    jsonInit("PATCH", { private: value }),
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
  skill?: string;
}

export type ChatScope = { type: "brain" } | { type: "notebook"; id: string };

export function askBrain(
  question: string,
  settings: Settings,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
  scope?: ChatScope,
) {
  return request<ChatResult>(
    "/chat",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...providerHeaders(settings),
      },
      body: JSON.stringify(scope ? { question, scope } : { question }),
    },
    baseUrl,
    fetcher,
  );
}

export interface NotebookSummary {
  id: string;
  name: string;
  rules: Rule[];
  member_count: number;
}

export interface Pin {
  source_id: string;
  mode: "in" | "out";
}

export interface Notebook {
  id: string;
  name: string;
  rules: Rule[];
  pins: Pin[];
}

export type NotebookMember = Source & { reasons: Reason[] };

export function listNotebooks(
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<NotebookSummary[]>("/notebooks", undefined, baseUrl, fetcher);
}

export function getNotebook(
  id: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Notebook>(`/notebooks/${id}`, undefined, baseUrl, fetcher);
}

export function createNotebook(
  name: string,
  rules: Rule[],
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Notebook>(
    "/notebooks",
    jsonInit("POST", { name, rules }),
    baseUrl,
    fetcher,
  );
}

export function updateNotebook(
  id: string,
  patch: { name?: string; rules?: Rule[] },
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<Notebook>(
    `/notebooks/${id}`,
    jsonInit("PATCH", patch),
    baseUrl,
    fetcher,
  );
}

export function deleteNotebook(
  id: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<void>(
    `/notebooks/${id}`,
    { method: "DELETE" },
    baseUrl,
    fetcher,
  );
}

export function notebookSources(
  id: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<NotebookMember[]>(
    `/notebooks/${id}/sources`,
    undefined,
    baseUrl,
    fetcher,
  );
}

export function pinSource(
  id: string,
  sourceId: string,
  mode: "in" | "out",
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<{ notebook_id: string; source_id: string; mode: string }>(
    `/notebooks/${id}/pins/${sourceId}`,
    jsonInit("PUT", { mode }),
    baseUrl,
    fetcher,
  );
}

export function unpinSource(
  id: string,
  sourceId: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  return request<void>(
    `/notebooks/${id}/pins/${sourceId}`,
    { method: "DELETE" },
    baseUrl,
    fetcher,
  );
}

export function listActivity(
  notebookId?: string,
  baseUrl = API_URL,
  fetcher: typeof fetch = fetch,
) {
  const query = notebookId
    ? `?notebook_id=${encodeURIComponent(notebookId)}`
    : "";
  return request<ActivityEvent[]>(
    `/activity${query}`,
    undefined,
    baseUrl,
    fetcher,
  );
}

export function listSkills(baseUrl = API_URL, fetcher: typeof fetch = fetch) {
  return request<SkillInfo[]>("/skills", undefined, baseUrl, fetcher);
}
