import { describe, expect, test } from "bun:test";
import { formatSize, hasPending, positionLabel, stateLabel } from "./sources";

describe("sources helpers", () => {
  test("formatSize uses human units", () => {
    expect(formatSize(512)).toBe("512 B");
    expect(formatSize(2048)).toBe("2.0 KB");
    expect(formatSize(5 * 1024 * 1024)).toBe("5.0 MB");
  });

  test("hasPending is true while any source is processing", () => {
    expect(hasPending([{ state: "ready" }, { state: "processing" }])).toBe(
      true,
    );
    expect(hasPending([{ state: "ready" }, { state: "failed" }])).toBe(false);
    expect(hasPending([])).toBe(false);
  });

  test("stateLabel is readable", () => {
    expect(stateLabel("processing")).toBe("Processing");
    expect(stateLabel("ready")).toBe("Ready");
    expect(stateLabel("failed")).toBe("Failed");
  });
});

describe("positionLabel", () => {
  test("describes pages, sheet rows and unpositioned sources", () => {
    expect(positionLabel({ page: 3 })).toBe("p.3");
    expect(positionLabel({ sheet: "Q1", rows: [2, 51] })).toBe(
      "sheet Q1, rows 2–51",
    );
    expect(positionLabel({})).toBe("");
  });
});
