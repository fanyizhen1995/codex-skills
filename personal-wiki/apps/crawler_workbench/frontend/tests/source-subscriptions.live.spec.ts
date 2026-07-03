import { expect, test } from "@playwright/test";
import { spawn, spawnSync, type ChildProcessWithoutNullStreams } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const backendPort = Number(process.env.PW_WORKBENCH_E2E_BACKEND_PORT ?? "18765");
const backendUrl = process.env.PW_WORKBENCH_E2E_BACKEND_URL ?? `http://127.0.0.1:${backendPort}`;
const repoRoot = path.resolve(__dirname, "../../../../..");
const backendDir = path.join(repoRoot, "personal-wiki/apps/crawler_workbench/backend");
const runDomainChannels = process.env.PW_WORKBENCH_E2E_DOMAIN_CHANNELS === "1";
const domainChannelSecret = process.env.PW_WORKBENCH_E2E_DOMAIN_CHANNEL_SECRET ?? "domain-channel-live-ui-secret";

let stateDir = "";
let backendProcess: ChildProcessWithoutNullStreams | undefined;
let backendExited = false;
let backendExitCode: number | null = null;
let backendExitSignal: NodeJS.Signals | null = null;

test.beforeAll(async () => {
  stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "crawler-workbench-source-e2e-"));
  seedBackendState(stateDir);
  backendProcess = startBackend(stateDir);
  await waitForBackend();
});

test.afterAll(async () => {
  if (backendProcess !== undefined) {
    if (!backendExited) {
      backendProcess.kill("SIGTERM");
      await new Promise((resolve) => backendProcess?.once("exit", resolve));
    }
  }
  if (stateDir) {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("user trusts same-site accelerator candidates from the source subscription page", async ({ page }) => {
  const trustRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/accelerator-candidates/") && request.url().endsWith("/trust-source")) {
      trustRequests.push(request.url());
    }
  });

  await page.goto("/");
  await page.getByRole("button", { name: /来源订阅/ }).click();
  await expect(page.getByRole("heading", { name: "来源订阅" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "新硬件候选" })).toBeVisible();
  await expect(page.getByRole("button", { name: "信任同站 E2E-G900" })).toBeVisible();

  await page.getByRole("button", { name: "信任同站 E2E-G900" }).click();

  await expect(page.getByText("已信任 e2e.example.com，同站接受 2 个候选")).toBeVisible();
  await expect(page.getByText("暂无新硬件候选")).toBeVisible();
  await expect(page.getByText("e2evendor E2E-G900 accelerator specs")).toBeVisible();
  await expect(page.getByText("e2evendor E2E-G901 accelerator specs")).toBeVisible();
  expect(trustRequests).toHaveLength(1);

  const response = await fetch(`${backendUrl}/api/accelerator-candidates`);
  expect(response.ok).toBe(true);
  const candidates = (await response.json()) as Array<{ model_name: string; status: string; accepted_source_id: string }>;
  expect(
    candidates
      .filter((candidate) => candidate.model_name.startsWith("E2E-"))
      .map(({ model_name, status, accepted_source_id }) => ({ model_name, status, accepted_source_id }))
  ).toEqual([
    {
      model_name: "E2E-G900",
      status: "accepted",
      accepted_source_id: "compute-accelerators-e2evendor-e2eg900"
    },
    {
      model_name: "E2E-G901",
      status: "accepted",
      accepted_source_id: "compute-accelerators-e2evendor-e2eg901"
    }
  ]);
});

test("user manages domain channel access and child sources", async ({ page }) => {
  test.skip(!runDomainChannels, "Domain Channels flow is enabled by the evaluator helper.");

  await page.goto("/");
  await page.getByRole("button", { name: /渠道管理/ }).click();
  await expect(page.getByRole("heading", { name: "Domain Channels" })).toBeVisible();
  await expect(page.getByText("https://e2e.example.com").first()).toBeVisible();

  await page.getByLabel("Channel name").fill("Live GitHub");
  await page.getByLabel("Base URL").fill("https://github.com");
  await page.getByLabel("Probe URL").fill(`${backendUrl}/api/health`);
  await page.getByLabel("Connector").selectOption("github");
  await page.getByLabel("Auth mode").selectOption("token");
  await page.getByLabel("Channel notes").fill("Live evaluator synthetic channel");
  await page.getByText("Auth required").click();
  await page.getByRole("button", { name: "Add channel" }).click();
  await expect(page.getByRole("row", { name: "Select channel Live GitHub" })).toBeVisible();

  await page.getByRole("row", { name: "Select channel Live GitHub" }).click();
  await page.getByLabel("Secret value").fill(domainChannelSecret);
  await page.getByRole("button", { name: "Replace secret" }).click();
  await expect(page.getByLabel("Secret value")).toHaveValue("");
  await expect(page.locator(`input[value="${domainChannelSecret}"]`)).toHaveCount(0);
  await expect(page.getByText(/token · secret configured/)).toBeVisible();

  await page.getByRole("button", { name: "Verify access" }).click();
  await expect(page.getByText("Probe #")).toBeVisible();

  await page.getByLabel("Source id").fill("domain-channel-live-nccl");
  await page.getByLabel("Source name").fill("Domain Channel Live NCCL");
  await page.getByLabel("Source URL").fill("https://github.com/NVIDIA/nccl");
  await page.getByLabel("Fetcher type").selectOption("github_repo");
  await page.getByLabel("Topic").fill("NCCL repository through live channel");
  await page.getByRole("button", { name: "Add child source" }).click();
  await expect(page.getByLabel("Channel details").getByText("Domain Channel Live NCCL", { exact: true })).toBeVisible();

  const channelsResponse = await fetch(`${backendUrl}/api/channels?domain=ai_infra`);
  expect(channelsResponse.ok).toBe(true);
  const channels = (await channelsResponse.json()) as Array<{
    id: string;
    name: string;
    auth_state: string;
    secret_configured: boolean;
    source_count: number;
  }>;
  const channel = channels.find((candidate) => candidate.name === "Live GitHub");
  expect(channel).toBeTruthy();
  expect(channel?.secret_configured).toBe(true);
  expect(channel?.auth_state).not.toBe("needs_auth_config");

  const sourcesResponse = await fetch(`${backendUrl}/api/sources?domain=ai_infra&channel_id=${channel?.id}`);
  expect(sourcesResponse.ok).toBe(true);
  const sources = (await sourcesResponse.json()) as Array<{ id: string; channel_id: string; fetcher_type: string }>;
  expect(sources).toContainEqual(
    expect.objectContaining({
      id: "domain-channel-live-nccl",
      channel_id: channel?.id,
      fetcher_type: "github_repo"
    })
  );
});

function seedBackendState(nextStateDir: string) {
  fs.writeFileSync(
    path.join(nextStateDir, "sources.yaml"),
    `sources:
- id: compute-accelerator-discovery-e2e-products
  name: E2E accelerator discovery
  type: web
  target_domain: ai_infra
  url: https://e2e.example.com/products/
  trust_level: trusted
  schedule: monthly
  auto_ingest: false
  auth_required: false
  topic: E2E accelerator discovery
  run_policy: scheduled
  discovery_mode: accelerator_models
  extract_mode: discovery_index
  vendor_hint: e2evendor
  accelerator_scope:
    - gpu
`
  );
  const script = `
from pathlib import Path
import sys

from crawler_workbench.db import migrate, open_db, transaction
from crawler_workbench.profiles import load_profiles_from_yaml, mirror_profiles

state_dir = Path(sys.argv[1])
with open_db(state_dir / "workbench.sqlite3") as db:
    migrate(db)
    with transaction(db):
        mirror_profiles(db, load_profiles_from_yaml(state_dir / "sources.yaml"))
        for model, normalized, url in [
            ("E2E-G900", "E2EG900", "https://e2e.example.com/products/e2e-g900/"),
            ("E2E-G901", "E2EG901", "https://www.e2e.example.com/products/e2e-g901/"),
        ]:
            db.execute(
                """
                insert into accelerator_candidates (
                  vendor, model_name, normalized_model, scope, source_profile_id,
                  source_url, evidence_url, evidence_text, confidence, status
                )
                values (?, ?, ?, 'gpu', 'compute-accelerator-discovery-e2e-products', ?, ?, ?, 0.95, 'pending')
                """,
                ("e2evendor", model, normalized, url, url, f"{model} GPU accelerator"),
            )
`;
  const result = spawnSync("python3", ["-c", script, nextStateDir], {
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: backendDir
    },
    encoding: "utf-8"
  });
  if (result.status !== 0) {
    throw new Error(`failed to seed backend state\n${result.stdout}\n${result.stderr}`);
  }
}

function startBackend(nextStateDir: string) {
  const child = spawn(
    "python3",
    ["-m", "uvicorn", "crawler_workbench.main:app", "--host", "127.0.0.1", "--port", String(backendPort)],
    {
      cwd: backendDir,
      env: {
        ...process.env,
        PYTHONPATH: backendDir,
        PW_WORKBENCH_DISABLE_SCHEDULER: "1",
        PW_WORKBENCH_REPO_ROOT: repoRoot,
        PW_WORKBENCH_STATE_DIR: nextStateDir,
        PW_WORKBENCH_BIND_HOST: "127.0.0.1",
        PW_WORKBENCH_BIND_PORT: String(backendPort)
      }
    }
  );
  child.once("exit", (code, signal) => {
    backendExited = true;
    backendExitCode = code;
    backendExitSignal = signal;
  });
  child.stdout.on("data", (chunk) => process.stdout.write(`[backend] ${chunk}`));
  child.stderr.on("data", (chunk) => process.stderr.write(`[backend] ${chunk}`));
  return child;
}

async function waitForBackend() {
  const startedAt = Date.now();
  while (Date.now() - startedAt < 20_000) {
    if (backendExited) {
      throw new Error(`backend exited before becoming healthy: code=${backendExitCode} signal=${backendExitSignal}`);
    }
    try {
      const response = await fetch(`${backendUrl}/api/health`);
      if (response.ok) {
        await verifyBackendSettings();
        return;
      }
    } catch {
      // Keep polling until uvicorn has bound the port.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`backend did not become healthy at ${backendUrl}`);
}

async function verifyBackendSettings() {
  const response = await fetch(`${backendUrl}/api/settings`);
  if (!response.ok) {
    throw new Error(`backend settings check failed: ${response.status}`);
  }
  const settings = (await response.json()) as { database_path?: string };
  const expectedDatabasePath = path.join(stateDir, "workbench.sqlite3");
  if (settings.database_path !== expectedDatabasePath) {
    throw new Error(`backend is not using isolated state: ${settings.database_path ?? "<missing>"}`);
  }
}
