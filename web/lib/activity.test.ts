import { describe, expect, test } from "bun:test";
import { activityLabel } from "./activity";

describe("activityLabel", () => {
  test("uses plain words for each kind", () => {
    expect(activityLabel("added")).toBe("Added");
    expect(activityLabel("edited")).toBe("Edited");
    expect(activityLabel("removed")).toBe("Removed");
  });
});
