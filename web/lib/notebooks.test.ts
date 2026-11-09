import { describe, expect, test } from "bun:test";
import { reasonLabel, ruleLabel } from "./notebooks";

describe("notebook labels", () => {
  test("ruleLabel names each rule type", () => {
    expect(ruleLabel({ type: "file_type", value: "spreadsheet" })).toBe(
      "File type: spreadsheet",
    );
    expect(ruleLabel({ type: "keyword", value: "invoice" })).toBe(
      'Keyword: "invoice"',
    );
    expect(ruleLabel({ type: "tag", value: "billing" })).toBe("Tag: #billing");
  });

  test("reasonLabel explains why a source is a member", () => {
    expect(reasonLabel({ via: "pin" })).toBe("Pinned in");
    expect(
      reasonLabel({ via: "rule", rule: { type: "tag", value: "billing" } }),
    ).toBe("Rule · Tag: #billing");
  });
});
