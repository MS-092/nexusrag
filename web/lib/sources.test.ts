import { describe, expect, test } from "bun:test";
import { formatSize, hasPending, stateLabel } from "./sources";

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
