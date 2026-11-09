import type { SourceState } from "@/lib/api";

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function hasPending(sources: { state: SourceState }[]): boolean {
  return sources.some((s) => s.state === "processing");
}

const LABELS: Record<SourceState, string> = {
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

export function stateLabel(state: SourceState): string {
  return LABELS[state];
}

/** File extensions the API accepts. Grows with each Source kind. */
export const ACCEPT = ".pdf,.csv,.xlsx,.png,.jpg,.jpeg";

export function positionLabel(position: {
  page?: number;
  sheet?: string;
  rows?: [number, number];
}): string {
  if (position.sheet && position.rows)
    return `sheet ${position.sheet}, rows ${position.rows[0]}–${position.rows[1]}`;
  if (position.page) return `p.${position.page}`;
  return "";
}
