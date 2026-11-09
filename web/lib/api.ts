import { API_URL } from "@/lib/health";

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
) {
  const form = new FormData();
  form.append("file", file);
  return request<Source>(
    "/sources",
    { method: "POST", body: form },
    baseUrl,
    fetcher,
  );
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
