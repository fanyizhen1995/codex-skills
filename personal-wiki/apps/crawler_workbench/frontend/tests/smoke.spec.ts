import { expect, test } from "@playwright/test";

test("workbench pages render", async ({ page }) => {
  await page.route("**/api/domains", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([{ id: "ai_infra", name: "ai_infra" }])
    })
  );
  await page.route("**/api/graph?*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ nodes: [], edges: [] })
    })
  );

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "运维控制台" })).toBeVisible();
  await expect(page.getByText("无登录")).toBeVisible();
  await page.getByRole("button", { name: /知识工作台/ }).click();
  await expect(page.getByRole("heading", { name: "Codex 查询" })).toBeVisible();
  await page.getByRole("button", { name: /来源工作台/ }).click();
  await expect(page.getByRole("heading", { name: "来源覆盖" })).toBeVisible();
});
