import { describe, expect, test } from "bun:test";
import { matchingSkills } from "./skills";

const skills = [
  { name: "summarize", description: "", usage: "/summarize" },
  { name: "status", description: "", usage: "/status" },
];

describe("matchingSkills", () => {
  test("suggests skills while the input starts with a slash", () => {
    expect(matchingSkills("/", skills).map((s) => s.name)).toEqual([
      "summarize",
      "status",
    ]);
    expect(matchingSkills("/su", skills).map((s) => s.name)).toEqual([
      "summarize",
    ]);
  });

  test("suggests nothing for ordinary questions or after the command word", () => {
    expect(matchingSkills("what is /etc?", skills)).toEqual([]);
    expect(matchingSkills("/summarize finance.pdf", skills)).toEqual([]);
    expect(matchingSkills("", skills)).toEqual([]);
  });
});
