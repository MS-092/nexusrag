import { expect, test } from "@playwright/test";
import { readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { join } from "node:path";
import { E2E_DATA_DIR } from "../playwright.config";
import { tinyPdf } from "./pdf";

const KEY = "sk-e2e-SECRET-0123456789abcdef";
const API = "http://127.0.0.1:8000";
const PROVIDER = "http://127.0.0.1:4010";

function filesUnder(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? filesUnder(path) : [path];
  });
}

test.afterAll(() => {
  rmSync(E2E_DATA_DIR, { recursive: true, force: true });
});

test("set key, upload, ask, open a citation, and the key lives only in browser storage", async ({
  page,
  request,
}) => {
  await page.goto("/");

  // 1. Configure a provider with a key (stored in this browser only).
  await page.getByRole("button", { name: "Settings" }).click();
  const dialog = page.getByRole("dialog", { name: "AI provider" });
  await dialog
    .getByRole("combobox", { name: /Provider/ })
    .selectOption("openai-compatible");
  await dialog.getByLabel("Base URL").fill(PROVIDER);
  await dialog.getByLabel(/^Model/).fill("test-model");
  await dialog.getByLabel(/^API key/).fill(KEY);
  await dialog.getByRole("button", { name: "Save" }).click();
  await expect(dialog).toBeHidden();

  // 2. Upload a PDF and wait for it to become ready.
  await page.locator('input[type="file"]').setInputFiles({
    name: "report.pdf",
    mimeType: "application/pdf",
    buffer: tinyPdf("Revenue in Q3 was 4.2 million dollars."),
  });
  await expect(page.getByText("report.pdf")).toBeVisible();
  await expect(page.getByText("Ready", { exact: true })).toBeVisible();

  // 3. Ask a question and read the cited answer.
  await page.getByRole("button", { name: "Chat" }).click();
  await page.getByLabel("Ask your Brain").fill("What was revenue in Q3?");
  await page.getByLabel("Ask your Brain").press("Enter");
  await expect(
    page.getByText("Revenue in Q3 was 4.2 million dollars [1]."),
  ).toBeVisible();

  // 4. Open the citation and see the cited passage.
  const citation = page.getByText("report.pdf · p.1");
  await expect(citation).toBeVisible();
  await citation.click();
  await expect(
    page.getByText("Revenue in Q3 was 4.2 million dollars.").last(),
  ).toBeVisible();

  // 5. The key exists in browser localStorage, and nowhere else.
  const storage = await page.evaluate(() => ({
    local: JSON.stringify({ ...localStorage }),
    session: JSON.stringify({ ...sessionStorage }),
    cookie: document.cookie,
  }));
  expect(storage.local).toContain(KEY);
  expect(storage.session).not.toContain(KEY);
  expect(storage.cookie).not.toContain(KEY);

  // The provider received it per request (that is what BYOK means)...
  const seen = (await (await request.get(`${PROVIDER}/__requests`)).json()) as {
    headers: Record<string, string>;
  }[];
  expect(seen.length).toBeGreaterThan(0);
  expect(seen[0].headers["authorization"]).toBe(`Bearer ${KEY}`);

  // ...but the NexusRAG API never returns it...
  for (const path of [
    "/sources",
    "/conversations",
    "/notebooks",
    "/activity",
    "/health",
  ]) {
    expect(await (await request.get(`${API}${path}`)).text()).not.toContain(
      KEY,
    );
  }

  // ...and never wrote it to disk.
  const files = filesUnder(E2E_DATA_DIR);
  expect(files.length).toBeGreaterThan(0);
  for (const file of files) {
    expect(readFileSync(file).includes(KEY), `key leaked into ${file}`).toBe(
      false,
    );
  }
});
