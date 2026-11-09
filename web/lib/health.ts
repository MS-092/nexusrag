export interface ComponentStatus {
  status: string;
  detail?: string;
}

export interface Health {
  status: string;
  embedder: ComponentStatus;
  index: ComponentStatus;
  storage: ComponentStatus;
}

export interface HealthRow {
  name: string;
  status: string;
}

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function fetchHealth(
  baseUrl: string = API_URL,
  fetcher: typeof fetch = fetch,
): Promise<Health> {
  let res: Response;
  try {
    res = await fetcher(`${baseUrl}/health`);
  } catch {
    throw new Error(
      "Cannot reach the NexusRAG API. Is it running on this machine?",
    );
  }
  if (!res.ok) throw new Error(`API returned ${res.status}`);
  return (await res.json()) as Health;
}

export function summarizeHealth(health: Health): HealthRow[] {
  return [
    { name: "Storage", status: health.storage.status },
    { name: "Embedder", status: health.embedder.status },
    { name: "Index", status: health.index.status },
  ];
}
