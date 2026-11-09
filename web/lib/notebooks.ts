export type RuleType = "file_type" | "keyword" | "tag";

export interface Rule {
  type: RuleType;
  value: string;
}

export type Reason = { via: "pin" } | { via: "rule"; rule: Rule };

export function ruleLabel(rule: Rule): string {
  if (rule.type === "file_type") return `File type: ${rule.value}`;
  if (rule.type === "keyword") return `Keyword: "${rule.value}"`;
  return `Tag: #${rule.value}`;
}

export function reasonLabel(reason: Reason): string {
  return reason.via === "pin"
    ? "Pinned in"
    : `Rule · ${ruleLabel(reason.rule)}`;
}
