import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

test("static app document has the workbench title", async () => {
  const html = await readFile(join(process.cwd(), "index.html"), "utf-8");

  expect(html).toContain("<title>Personal Wiki Crawler Workbench</title>");
});
