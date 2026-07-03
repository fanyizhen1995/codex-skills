import { expect, test, type Page } from "@playwright/test";

const githubChannel = {
  id: "github-com",
  target_domain: "ai_infra",
  name: "GitHub",
  base_url: "https://github.com",
  base_url_normalized: "https://github.com",
  probe_url: "https://api.github.com/user",
  probe_method: "GET",
  probe_config_json: "{}",
  kind: "web",
  connector: "github",
  trust_level: "trusted",
  enabled: true,
  auth_required: true,
  auth_mode: "token",
  auth_state: "ready",
  last_probe_status: "ready",
  last_probe_at: "2026-07-03 10:00:00",
  last_probe_summary: "HTTP 200 from api.github.com",
  secret_configured: true,
  notes: "GitHub token verified",
  source_count: 1,
  created_at: "2026-07-03 09:00:00",
  updated_at: "2026-07-03 10:00:00"
};

const githubIssueSource = {
  id: "nccl-github-issues",
  name: "NCCL GitHub issues",
  type: "github",
  fetcher_type: "github_issues",
  target_domain: "ai_infra",
  url: "https://github.com/NVIDIA/nccl/issues",
  channel_id: "github-com",
  channel_name: "GitHub",
  channel_base_url: "https://github.com",
  channel_auth_state: "ready",
  trust_level: "trusted",
  schedule: "daily",
  run_policy: "scheduled",
  auto_ingest: true,
  auth_required: false,
  auth_state: "ready",
  topic: "NCCL issues",
  enabled: true
};

async function routeCommonWorkbenchApis(page: Page) {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        bind_host: "0.0.0.0",
        bind_port: 8765,
        authenticated: false,
        warning: "无登录：仅可暴露在可信网络。后端可触发本机 Codex。"
      })
    })
  );
  await page.route("**/api/runs", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify([]) })
  );
  await page.route("**/api/queue", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify([]) })
  );
  await page.route("**/api/wiki/metrics", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        counts: {
          domain_count: 1,
          wiki_page_count: 0,
          raw_file_count: 0,
          raw_item_count: 0,
          total_file_count: 0
        },
        sizes: {
          total_bytes: 0,
          wiki_bytes: 0,
          raw_bytes: 0,
          global_bytes: 0,
          state_bytes: 0
        },
        health: {
          status: "healthy",
          score: 100,
          summary: "ok",
          latest_validation_status: "succeeded",
          latest_validation_at: "2026-07-03 10:00:00",
          failed_run_count: 0,
          failed_task_count: 0,
          pending_task_count: 0
        }
      })
    })
  );
  await page.route("**/api/jobs/latest?*", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify(null) })
  );
  await page.route("**/api/search?*", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify([]) })
  );
}

test("workbench pages render", async ({ page }) => {
  await routeCommonWorkbenchApis(page);
  await page.route("**/api/domains", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([{ id: "ai_infra", name: "ai_infra" }])
    })
  );
  await page.route("**/api/sources", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify([githubIssueSource]) })
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

test("domain channels flow manages channel access and child sources", async ({ page }) => {
  await routeCommonWorkbenchApis(page);
  const channels = [githubChannel];
  const sources = [githubIssueSource];
  const probeRuns = [
    {
      id: 7,
      channel_id: "github-com",
      status: "ready",
      started_at: "2026-07-03 10:00:00",
      finished_at: "2026-07-03 10:00:01",
      http_status: 200,
      final_url: "https://api.github.com/user",
      summary: "HTTP 200 from api.github.com",
      error: null
    }
  ];

  await page.route("**/api/domains", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([{ id: "ai_infra", name: "ai_infra" }])
    })
  );
  await page.route(/\/api\/channels(?:\?.*)?$/, async (route) => {
    if (route.request().method() === "POST") {
      const payload = route.request().postDataJSON();
      channels.push({
        ...githubChannel,
        id: "arxiv-org",
        name: payload.name,
        base_url: payload.base_url,
        base_url_normalized: payload.base_url,
        probe_url: payload.probe_url || payload.base_url,
        connector: payload.connector,
        auth_required: payload.auth_required,
        auth_mode: payload.auth_mode,
        secret_configured: false,
        notes: payload.notes,
        source_count: 0
      });
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(channels.at(-1)) });
      return;
    }
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(channels) });
  });
  await page.route("**/api/channels/github-com/secret", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        channel_id: "github-com",
        secret_kind: "synthetic_token",
        secret_configured: true,
        auth_state: "ready"
      })
    })
  );
  await page.route(/\/api\/channels\/[^/]+\/probe-runs$/, (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify(probeRuns) })
  );
  await page.route("**/api/channels/github-com/probe", (route) => {
    const run = {
      id: 8,
      channel_id: "github-com",
      status: "ready",
      started_at: "2026-07-03 10:05:00",
      finished_at: "2026-07-03 10:05:01",
      http_status: 200,
      final_url: "https://api.github.com/user",
      summary: "HTTP 200 from api.github.com",
      error: null
    };
    probeRuns.unshift(run);
    return route.fulfill({ contentType: "application/json", body: JSON.stringify(run) });
  });
  await page.route(/\/api\/sources(?:\?.*)?$/, async (route) => {
    if (route.request().method() === "POST") {
      const payload = route.request().postDataJSON();
      const source = {
        ...githubIssueSource,
        ...payload,
        channel_name: "GitHub",
        channel_base_url: "https://github.com",
        channel_auth_state: "ready",
        auth_state: "ready"
      };
      sources.push(source);
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(source) });
      return;
    }
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(sources) });
  });
  await page.route("**/api/accelerator-candidates", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify([]) })
  );

  await page.goto("/");
  await page.getByRole("button", { name: /渠道管理/ }).click();
  await expect(page.getByRole("heading", { name: "Domain Channels" })).toBeVisible();
  await expect(page.getByText("https://github.com").first()).toBeVisible();
  await expect(page.getByText("NCCL GitHub issues")).toBeVisible();

  await page.getByLabel("Channel name").fill("arXiv");
  await page.getByLabel("Base URL").fill("https://arxiv.org");
  await page.getByLabel("Connector").selectOption("arxiv");
  await page.getByLabel("Channel notes").fill("Public paper source");
  await page.getByRole("button", { name: "Add channel" }).click();
  await expect(page.getByRole("row", { name: "Select channel arXiv" })).toBeVisible();

  await page.getByRole("row", { name: "Select channel GitHub" }).click();
  await page.getByLabel("Secret value").fill("synthetic-secret-123");
  await page.getByRole("button", { name: "Replace secret" }).click();
  await expect(page.getByLabel("Secret value")).toHaveValue("");
  await expect(page.locator('input[value="synthetic-secret-123"]')).toHaveCount(0);

  await page.getByRole("button", { name: "Verify access" }).click();
  await expect(page.getByText("Probe #8")).toBeVisible();

  await page.getByLabel("Source id").fill("nccl-github-releases");
  await page.getByLabel("Source name").fill("NCCL GitHub releases");
  await page.getByLabel("Source URL").fill("https://github.com/NVIDIA/nccl/releases");
  await page.getByLabel("Fetcher type").selectOption("github_releases");
  await page.getByLabel("Topic").fill("NCCL releases");
  await page.getByRole("button", { name: "Add child source" }).click();
  await expect(page.getByLabel("Channel details").getByText("NCCL GitHub releases", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /来源订阅/ }).click();
  await expect(page.getByRole("heading", { name: "来源订阅" })).toBeVisible();
  await page.getByRole("button", { name: /入库队列/ }).click();
  await expect(page.getByRole("heading", { name: "入库队列" })).toBeVisible();
});
