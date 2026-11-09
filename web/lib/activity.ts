export type ActivityKind = "added" | "edited" | "removed";

export interface ActivityEvent {
  id: number;
  kind: ActivityKind;
  source_id: string;
  source_name: string;
  notebook_ids: string[];
  created_at: string;
}

const LABELS: Record<ActivityKind, string> = {
  added: "Added",
  edited: "Edited",
  removed: "Removed",
};

export function activityLabel(kind: ActivityKind): string {
  return LABELS[kind];
}
