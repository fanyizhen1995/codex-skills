import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { AcceleratorCandidate, AcceleratorSpecRecord } from "./types";
import {
  acceptAcceleratorCandidate,
  createManualIngest,
  createChannel,
  createSource,
  extractAcceleratorSpecs,
  getAcceleratorCandidates,
  getAcceleratorSpecs,
  getChannelProbeRuns,
  getChannels,
  getQueue,
  getRuns,
  getSources,
  getSourcesForChannel,
  getJob,
  getLatestJob,
  getWikiPage,
  getWikiPages,
  getWikiMetrics,
  probeChannel,
  rejectAcceleratorCandidate,
  setChannelSecret,
  updateChannel,
  trustAcceleratorCandidateSource,
  trustQueueSource,
  validateWiki
} from "./api";

function defaultWikiMetrics() {
  return {
    counts: {
      domain_count: 1,
      wiki_page_count: 3,
      raw_file_count: 2,
      raw_item_count: 2,
      total_file_count: 8
    },
    sizes: {
      total_bytes: 2048,
      wiki_bytes: 1024,
      raw_bytes: 768,
      global_bytes: 256,
      state_bytes: 0
    },
    health: {
      status: "healthy",
      score: 100,
      summary: "轻量健康度：正常",
      latest_validation_status: "succeeded",
      latest_validation_at: "2026-06-26 02:00:00",
      failed_run_count: 0,
      failed_task_count: 0,
      pending_task_count: 0
    }
  };
}

const mockWikiMetrics = {
  counts: {
    domain_count: 1,
    wiki_page_count: 3,
    raw_file_count: 2,
    raw_item_count: 2,
    total_file_count: 8
  },
  sizes: {
    total_bytes: 2048,
    wiki_bytes: 1024,
    raw_bytes: 768,
    global_bytes: 256,
    state_bytes: 0
  },
  health: {
    status: "healthy",
    score: 100,
    summary: "轻量健康度：正常",
    latest_validation_status: "succeeded",
    latest_validation_at: "2026-06-26 02:00:00",
    failed_run_count: 0,
    failed_task_count: 0,
    pending_task_count: 0
  }
};

function mockAcceleratorCandidate(status: AcceleratorCandidate["status"] = "pending"): AcceleratorCandidate {
  return {
    id: 1,
    vendor: "nvidia",
    model_name: "H300",
    normalized_model: "h300",
    scope: "gpu",
    source_profile_id: "compute-accelerator-discovery-nvidia-products",
    source_url: "https://www.nvidia.com/en-us/data-center/products/",
    evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
    evidence_text: "NVIDIA H300 GPU accelerator",
    confidence: 0.85,
    status,
    created_at: "2026-06-28 01:00:00",
    updated_at: "2026-06-28 01:00:00"
  };
}

function mockAcceleratorSpec(): AcceleratorSpecRecord {
  return {
    sku_id: "biren-166l",
    vendor: "biren",
    model_name: "166l",
    normalized_model: "166L",
    scope: "ai_asic",
    source_profile_id: "compute-accelerators-biren-166l",
    source_url: "https://www.birentech.com/product/hardware/166l/",
    raw_item_id: 7,
    raw_path: "personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-biren-166l/item.md",
    observations: [
      {
        id: 9,
        field: "tdp",
        value_text: "600",
        value_number: 600,
        unit: "W",
        source_profile_id: "compute-accelerators-biren-166l",
        source_rank: "S1",
        raw_item_id: 7,
        raw_path: "personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-biren-166l/item.md",
        evidence_text: "峰值功耗 600W",
        confidence: 0.9
      },
      {
        id: 10,
        field: "memory_capacity",
        value_text: "256",
        value_number: 256,
        unit: "GB",
        source_profile_id: "compute-accelerators-biren-166l",
        source_rank: "S1",
        raw_item_id: 8,
        raw_path: "personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-biren-166l/memory.md",
        evidence_text: "显存容量 256GB HBM3e",
        confidence: 0.85
      }
    ],
    resolved_specs: [
      {
        field: "tdp",
        value_text: "600",
        value_number: 600,
        unit: "W",
        source_observation_id: 9,
        resolved_by: "rule",
        confidence: "0.9",
        conflict_status: "clean"
      }
    ]
  };
}

vi.mock("./api", () => ({
  askCodex: vi.fn(),
  approveTask: vi.fn(),
  acceptAcceleratorCandidate: vi.fn().mockResolvedValue({
    id: 1,
    vendor: "nvidia",
    model_name: "H300",
    normalized_model: "h300",
    scope: "gpu",
    source_profile_id: "compute-accelerator-discovery-nvidia-products",
    source_url: "https://www.nvidia.com/en-us/data-center/products/",
    evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
    evidence_text: "NVIDIA H300 GPU accelerator",
    confidence: 0.85,
    status: "accepted",
    created_at: "2026-06-28 01:00:00",
    updated_at: "2026-06-28 01:00:00"
  }),
  createManualIngest: vi.fn().mockResolvedValue({
    status: "succeeded",
    reason: "ingest succeeded",
    source_id: "manual-url-example-com-doc-9813a80c59",
    url: "https://example.com/doc",
    domain: "ai_infra",
    fetch: { fetch_run_id: 1, fetched_count: 1, changed_count: 1, skipped_count: 0 },
    task_id: 7,
    commit_sha: "abc1234"
  }),
  createChannel: vi.fn(),
  createSource: vi.fn(),
  extractAcceleratorSpecs: vi.fn().mockResolvedValue({ skus: 1, observations: 1, resolved: 1 }),
  getDomains: vi.fn().mockResolvedValue([{ id: "ai_infra", name: "ai_infra" }]),
  getAcceleratorCandidates: vi.fn().mockResolvedValue([]),
  getAcceleratorSpecs: vi.fn().mockResolvedValue([]),
  getChannelProbeRuns: vi.fn().mockResolvedValue([]),
  getChannels: vi.fn().mockResolvedValue([]),
  getGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  getHealth: vi.fn().mockResolvedValue({
    status: "ok",
    bind_host: "0.0.0.0",
    bind_port: 8765,
    authenticated: false,
    warning: "无登录：仅可暴露在可信网络。后端可触发本机 Codex。"
  }),
  getJob: vi.fn(),
  getLatestJob: vi.fn(),
  getQueue: vi.fn().mockResolvedValue([]),
  getRuns: vi.fn().mockResolvedValue([]),
  getSources: vi.fn().mockResolvedValue([]),
  getSourcesForChannel: vi.fn().mockResolvedValue([]),
  getWikiPage: vi.fn().mockResolvedValue({
    domain: "ai_infra",
    path: "projects/nccl.md",
    full_path: "personal-wiki/domains/ai_infra/wiki/projects/nccl.md",
    type: "project",
    title: "NCCL",
    description: "NCCL notes",
    status: "active",
    tags: ["nccl"],
    source_refs: ["../../raw/nccl.md"],
    content: "# NCCL\n\nNCCL content.",
    body: "NCCL content."
  }),
  getWikiPages: vi.fn().mockResolvedValue([
    {
      domain: "ai_infra",
      path: "projects/nccl.md",
      full_path: "personal-wiki/domains/ai_infra/wiki/projects/nccl.md",
      type: "project",
      title: "NCCL",
      description: "NCCL notes",
      status: "active",
      tags: ["nccl"],
      source_refs: ["../../raw/nccl.md"]
    }
  ]),
  getWikiMetrics: vi.fn().mockResolvedValue({
    counts: {
      domain_count: 1,
      wiki_page_count: 3,
      raw_file_count: 2,
      raw_item_count: 2,
      total_file_count: 8
    },
    sizes: {
      total_bytes: 2048,
      wiki_bytes: 1024,
      raw_bytes: 768,
      global_bytes: 256,
      state_bytes: 0
    },
    health: {
      status: "healthy",
      score: 100,
      summary: "轻量健康度：正常",
      latest_validation_status: "succeeded",
      latest_validation_at: "2026-06-26 02:00:00",
      failed_run_count: 0,
      failed_task_count: 0,
      pending_task_count: 0
    }
  }),
  rebuildSearch: vi.fn(),
  rejectAcceleratorCandidate: vi.fn().mockResolvedValue({
    id: 1,
    vendor: "nvidia",
    model_name: "H300",
    normalized_model: "h300",
    scope: "gpu",
    source_profile_id: "compute-accelerator-discovery-nvidia-products",
    source_url: "https://www.nvidia.com/en-us/data-center/products/",
    evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
    evidence_text: "NVIDIA H300 GPU accelerator",
    confidence: 0.85,
    status: "rejected",
    created_at: "2026-06-28 01:00:00",
    updated_at: "2026-06-28 01:00:00"
  }),
  rejectTask: vi.fn(),
  runSource: vi.fn(),
  searchWiki: vi.fn(),
  probeChannel: vi.fn(),
  setChannelSecret: vi.fn(),
  updateChannel: vi.fn(),
  trustQueueSource: vi.fn().mockResolvedValue({ domain: "vllm.ai", approved_count: 1 }),
  trustAcceleratorCandidateSource: vi.fn().mockResolvedValue({
    domain: "nvidia.com",
    accepted_count: 1,
    candidate_ids: [1],
    accepted_source_ids: ["compute-accelerators-nvidia-h300"],
    candidates: []
  }),
  validateWiki: vi.fn().mockResolvedValue({ status: "succeeded", stdout: "ok", stderr: "", validation_run_id: 7 })
}));

afterEach(() => {
  cleanup();
  vi.mocked(getAcceleratorCandidates).mockResolvedValue([]);
  vi.mocked(getAcceleratorSpecs).mockResolvedValue([]);
  vi.mocked(extractAcceleratorSpecs).mockResolvedValue({ skus: 1, observations: 1, resolved: 1 });
  vi.mocked(acceptAcceleratorCandidate).mockResolvedValue(mockAcceleratorCandidate("accepted"));
  vi.mocked(createManualIngest).mockResolvedValue({
    status: "succeeded",
    reason: "ingest succeeded",
    source_id: "manual-url-example-com-doc-9813a80c59",
    url: "https://example.com/doc",
    domain: "ai_infra",
    fetch: { fetch_run_id: 1, fetched_count: 1, changed_count: 1, skipped_count: 0 },
    task_id: 7,
    commit_sha: "abc1234"
  });
  vi.mocked(createChannel).mockResolvedValue({
    id: "arxiv-org",
    target_domain: "ai_infra",
    name: "arXiv",
    base_url: "https://arxiv.org",
    base_url_normalized: "https://arxiv.org",
    probe_url: "https://arxiv.org",
    probe_method: "GET",
    probe_config_json: "{}",
    kind: "web",
    connector: "arxiv",
    trust_level: "trusted",
    enabled: true,
    auth_required: false,
    auth_mode: "none",
    auth_state: "ready",
    last_probe_status: null,
    last_probe_at: null,
    last_probe_summary: null,
    secret_configured: false,
    notes: "Public paper source",
    source_count: 0,
    created_at: "2026-07-03 10:00:00",
    updated_at: "2026-07-03 10:00:00"
  });
  vi.mocked(createSource).mockResolvedValue({
    id: "nccl-github-releases",
    name: "NCCL GitHub releases",
    type: "github",
    fetcher_type: "github_releases",
    target_domain: "ai_infra",
    url: "https://github.com/NVIDIA/nccl/releases",
    channel_id: "github-com",
    channel_name: "GitHub",
    channel_base_url: "https://github.com",
    channel_auth_state: "ready",
    trust_level: "trusted",
    schedule: "weekly",
    run_policy: "scheduled",
    auto_ingest: true,
    auth_required: false,
    auth_state: "ready",
    topic: "NCCL releases",
    enabled: true
  });
  vi.mocked(getChannelProbeRuns).mockResolvedValue([]);
  vi.mocked(getChannels).mockResolvedValue([]);
  vi.mocked(probeChannel).mockResolvedValue({
    id: 8,
    channel_id: "github-com",
    status: "ready",
    started_at: "2026-07-03 10:05:00",
    finished_at: "2026-07-03 10:05:01",
    http_status: 200,
    final_url: "https://api.github.com/user",
    summary: "HTTP 200 from api.github.com",
    error: null
  });
  vi.mocked(setChannelSecret).mockResolvedValue({
    channel_id: "github-com",
    secret_kind: "synthetic_token",
    secret_configured: true,
    auth_state: "ready"
  });
  vi.mocked(updateChannel).mockImplementation(async (_id, payload) => ({
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
    notes: String(payload.notes ?? "GitHub token verified"),
    source_count: 1,
    created_at: "2026-07-03 09:00:00",
    updated_at: "2026-07-03 10:00:00"
  }));
  vi.mocked(rejectAcceleratorCandidate).mockResolvedValue(mockAcceleratorCandidate("rejected"));
  vi.mocked(getQueue).mockResolvedValue([]);
  vi.mocked(getRuns).mockResolvedValue([]);
  vi.mocked(getSources).mockResolvedValue([]);
  vi.mocked(getSourcesForChannel).mockResolvedValue([]);
  vi.mocked(getJob).mockResolvedValue({
    id: 42,
    status: "running",
    target_domain: "ai_infra",
    prompt: "使用 personal-wiki-manager，目标 domain: ai_infra，基于已有 wiki/raw 回答 \"横向对比\"",
    stdout: "",
    stderr: "",
    created_at: "2026-06-28 14:59:24"
  });
  vi.mocked(getLatestJob).mockResolvedValue(null);
  vi.mocked(getWikiPage).mockResolvedValue({
    domain: "ai_infra",
    path: "projects/nccl.md",
    full_path: "personal-wiki/domains/ai_infra/wiki/projects/nccl.md",
    type: "project",
    title: "NCCL",
    description: "NCCL notes",
    status: "active",
    tags: ["nccl"],
    source_refs: ["../../raw/nccl.md"],
    content: "# NCCL\n\nNCCL content.",
    body: "NCCL content."
  });
  vi.mocked(getWikiPages).mockResolvedValue([
    {
      domain: "ai_infra",
      path: "projects/nccl.md",
      full_path: "personal-wiki/domains/ai_infra/wiki/projects/nccl.md",
      type: "project",
      title: "NCCL",
      description: "NCCL notes",
      status: "active",
      tags: ["nccl"],
      source_refs: ["../../raw/nccl.md"]
    }
  ]);
  vi.mocked(getWikiMetrics).mockResolvedValue(defaultWikiMetrics());
  vi.mocked(trustQueueSource).mockResolvedValue({ domain: "vllm.ai", approved_count: 1 });
  vi.mocked(trustAcceleratorCandidateSource).mockResolvedValue({
    domain: "nvidia.com",
    accepted_count: 1,
    candidate_ids: [1],
    accepted_source_ids: ["compute-accelerators-nvidia-h300"],
    candidates: []
  });
  vi.mocked(validateWiki).mockResolvedValue({ status: "succeeded", stdout: "ok", stderr: "", validation_run_id: 7 });
});

describe("App", () => {
  it("renders the Chinese workbench shell with unauthenticated warning", async () => {
    render(<App />);

    expect(screen.getAllByText("运维控制台").length).toBeGreaterThan(0);
    expect(screen.getAllByText("知识工作台").length).toBeGreaterThan(0);
    expect(screen.getAllByText("来源工作台").length).toBeGreaterThan(0);
    expect(screen.getByText(/无登录/)).toBeInTheDocument();
    expect(screen.getByText("运行健康")).toBeInTheDocument();
    expect(screen.getByText("待处理入库")).toBeInTheDocument();
    expect(screen.getByText("抓取趋势")).toBeInTheDocument();
    expect(screen.getByText("来源覆盖")).toBeInTheDocument();
    expect(screen.getByText("失败原因分布")).toBeInTheDocument();

    fireEvent.click(screen.getAllByText("知识工作台")[0]);

    expect(screen.getAllByText("全文搜索").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Codex 查询").length).toBeGreaterThan(0);
    expect(screen.getAllByText("检索命中").length).toBeGreaterThan(0);
    expect(screen.getAllByText("知识关系图").length).toBeGreaterThan(0);
    expect(screen.queryByText("引用路径")).not.toBeInTheDocument();
    expect(screen.queryByText("相关 wiki 页面")).not.toBeInTheDocument();
    expect(screen.queryByText("主题时间线")).not.toBeInTheDocument();
  });

  it("loads knowledge domains from the API instead of hard-coded defaults", async () => {
    render(<App />);

    fireEvent.click(screen.getAllByText("知识工作台")[0]);

    const selector = await screen.findByLabelText("Domain");
    await waitFor(() => expect(selector).toHaveValue("ai_infra"));

    expect(screen.getByRole("option", { name: "ai_infra" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "engineering" })).not.toBeInTheDocument();
  });

  it("restores the latest Codex job when opening the knowledge page", async () => {
    vi.mocked(getLatestJob).mockResolvedValueOnce({
      id: 42,
      status: "running",
      target_domain: "ai_infra",
      prompt: "使用 personal-wiki-manager，目标 domain: ai_infra，基于已有 wiki/raw 回答 \"横向对比\"",
      stdout: "",
      stderr: "",
      created_at: "2026-06-28 14:59:24"
    });
    vi.mocked(getJob).mockResolvedValue({
      id: 42,
      status: "running",
      target_domain: "ai_infra",
      prompt: "使用 personal-wiki-manager，目标 domain: ai_infra，基于已有 wiki/raw 回答 \"横向对比\"",
      stdout: "",
      stderr: "",
      created_at: "2026-06-28 14:59:24"
    });

    render(<App />);

    fireEvent.click(screen.getAllByText("知识工作台")[0]);

    expect(await screen.findByText("任务状态：running")).toBeInTheDocument();
    expect(await screen.findByText(/任务 #42/)).toBeInTheDocument();
    expect(getLatestJob).toHaveBeenCalledWith("ai_infra");
  });

  it("renders Codex markdown answers as structured readable content", async () => {
    vi.mocked(getLatestJob).mockResolvedValueOnce({
      id: 43,
      status: "succeeded",
      target_domain: "ai_infra",
      prompt: "横向对比",
      stdout:
        "已基于 `ai_infra` 现有 wiki/raw 做了横向对比，并把可复用摘要沉淀到了： " +
        "[compute-accelerator-parameter-comparison.md](/home/fyz/codex-skills/personal-wiki/domains/ai_infra/wiki/references/compute-accelerator-parameter-comparison.md)\n\n" +
        "**结论速览**\n\n" +
        "| 类别 | 型号/记录 | 参数重点 |\n" +
        "| --- | --- | --- |\n" +
        "| 高端单卡/模块 | NVIDIA H200 SXM/NVL | 141 GB；NVLink 900 GB/s |\n" +
        "| 国产卡级对比 | Cambricon MLU370 | 参数较完整，可比 compute/memory/interface/power |\n\n" +
        "关键引用路径包括：\n" +
        "- [H200 raw](/home/fyz/codex-skills/personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-nvidia-h200/item.md)\n" +
        "- [unsafe](javascript:alert(1))",
      stderr: "",
      created_at: "2026-06-28 15:30:00"
    });

    render(<App />);

    fireEvent.click(screen.getAllByText("知识工作台")[0]);

    expect(await screen.findByText("结论速览")).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getByText("型号/记录")).toBeInTheDocument();
    expect(within(table).getByText("NVIDIA H200 SXM/NVL")).toBeInTheDocument();
    expect(screen.queryByText(/\|\s*---\s*\|/)).not.toBeInTheDocument();
    expect(screen.getByText("compute-accelerator-parameter-comparison.md")).toHaveAttribute(
      "title",
      expect.stringContaining("/home/fyz/codex-skills/")
    );
    expect(screen.getByText("H200 raw")).toHaveAttribute("title", expect.stringContaining("/raw/crawler/"));
    expect(screen.queryByRole("link", { name: "H200 raw" })).not.toBeInTheDocument();
    expect(document.querySelector('a[href^="javascript:"]')).not.toBeInTheDocument();
  });

  it("loads and renders wiki browser pages from the selected domain", async () => {
    render(<App />);

    fireEvent.click(screen.getAllByText("Wiki 浏览")[0]);

    expect(await screen.findByRole("button", { name: /NCCL/ })).toBeInTheDocument();
    expect(await screen.findByText("NCCL content.")).toBeInTheDocument();
    expect(screen.getAllByText("projects/nccl.md").length).toBeGreaterThan(0);
    expect(screen.getByText("../../raw/nccl.md")).toBeInTheDocument();
    expect(getWikiPages).toHaveBeenCalledWith("ai_infra");
    expect(getWikiPage).toHaveBeenCalledWith("ai_infra", "projects/nccl.md");
  });

  it("renders wiki markdown links safely and tolerates simple markdown edge cases", async () => {
    vi.mocked(getWikiPages).mockResolvedValueOnce([
      {
        domain: "ai_infra",
        path: "projects/nccl.md",
        full_path: "personal-wiki/domains/ai_infra/wiki/projects/nccl.md",
        type: "project",
        title: "NCCL",
        description: "NCCL notes",
        status: "active",
        tags: ["nccl"],
        source_refs: ["../../raw/nccl.md"]
      },
      {
        domain: "ai_infra",
        path: "references/nccl-release-notes.md",
        full_path: "personal-wiki/domains/ai_infra/wiki/references/nccl-release-notes.md",
        type: "reference",
        title: "NCCL Release Notes",
        description: "Release notes",
        status: "active",
        tags: ["nccl"],
        source_refs: []
      }
    ]);
    vi.mocked(getWikiPage).mockImplementation(async (_domain, path) => {
      if (path === "references/nccl-release-notes.md") {
        return {
          domain: "ai_infra",
          path,
          full_path: "personal-wiki/domains/ai_infra/wiki/references/nccl-release-notes.md",
          type: "reference",
          title: "NCCL Release Notes",
          description: "Release notes",
          status: "active",
          tags: ["nccl"],
          source_refs: [],
          content: "",
          body: "Release note detail."
        };
      }
      return {
        domain: "ai_infra",
        path: "projects/nccl.md",
        full_path: "personal-wiki/domains/ai_infra/wiki/projects/nccl.md",
        type: "project",
        title: "NCCL",
        description: "NCCL notes",
        status: "active",
        tags: ["nccl"],
        source_refs: ["../../raw/nccl.md"],
        content: "",
        body:
          "[safe](https://example.com/doc) and [bad](javascript:alert(1))\n\n" +
          "[release notes](../references/nccl-release-notes.md)\n\n" +
          "[capture](../../raw/crawler/compute/item.md)\n\n" +
          "- list item\n\n" +
          "| Name | Value |\n" +
          "| --- | --- |\n" +
          "| row | cell |\n\n" +
          "```\n" +
          "unfinished code"
      };
    });

    render(<App />);

    fireEvent.click(screen.getAllByText("Wiki 浏览")[0]);

    expect(await screen.findByRole("link", { name: "safe" })).toHaveAttribute("href", "https://example.com/doc");
    expect(screen.queryByRole("link", { name: "bad" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "capture" })).not.toBeInTheDocument();
    expect(screen.getByText("capture")).toHaveAttribute("title", expect.stringContaining("../../raw/crawler/compute/item.md"));
    expect(screen.getByText((_, element) => element?.tagName === "P" && element.textContent?.includes("bad"))).toBeInTheDocument();
    expect(screen.getByText("list item")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("cell")).toBeInTheDocument();
    expect(screen.getByText("unfinished code")).toBeInTheDocument();
    expect(document.querySelector('a[href^="javascript:"]')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "release notes" }));
    await screen.findByText("Release note detail.");
    expect(getWikiPage).toHaveBeenLastCalledWith("ai_infra", "references/nccl-release-notes.md");
    fireEvent.click(screen.getByRole("button", { name: /NCCL Release Notes/ }));
    await screen.findByText("Release note detail.");
    fireEvent.change(screen.getByLabelText("过滤 Wiki 页面"), { target: { value: "release" } });
    expect(screen.queryByRole("button", { name: /^NCCL projects/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /NCCL Release Notes/ })).toBeInTheDocument();
  });

  it("does not render sample content when live APIs return empty data", async () => {
    render(<App />);

    await screen.findByText("暂无计划抓取");
    expect(screen.queryByText("稳定")).not.toBeInTheDocument();
    expect(screen.queryByText("Engineering RSS")).not.toBeInTheDocument();
    expect(screen.queryByText("GitHub Watch")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByText("来源订阅")[0]);
    await screen.findByText("暂无来源订阅");
    expect(screen.queryByText("Arxiv AI")).not.toBeInTheDocument();
    expect(screen.queryByText("News Site")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByText("入库队列")[0]);
    await screen.findByText("暂无待人工处理任务");
    expect(screen.queryByText("Runtime incident notes")).not.toBeInTheDocument();
    expect(screen.queryByText("Market brief")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByText("知识工作台")[0]);
    await screen.findByText("暂无结果");
    expect(screen.queryByText("engineering/crawler-workbench.md")).not.toBeInTheDocument();
    expect(screen.queryByText("research/personal-wiki-manager.md")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByText("来源工作台")[0]);
    await screen.findByText("暂无来源覆盖数据");
    expect(screen.queryByText("暂无主题热力数据")).toBeInTheDocument();
  });

  it("summarizes real run error text in failure summaries", async () => {
    vi.mocked(getRuns).mockResolvedValue([
      {
        id: 21,
        source_id: "nccl-arxiv-papers",
        status: "failed",
        error: "The read operation timed out"
      }
    ]);

    render(<App />);

    expect(await screen.findByText("运行失败")).toBeInTheDocument();
    expect(screen.getAllByText("网络超时").length).toBeGreaterThan(0);
    expect(screen.getAllByText("1 次").length).toBeGreaterThan(0);
    expect(screen.queryByText(/The read operation timed out/)).not.toBeInTheDocument();
    expect(screen.queryByText("nccl-arxiv-papers：failed")).not.toBeInTheDocument();
    expect(screen.queryByText("运行 #21 失败")).not.toBeInTheDocument();
  });

  it("groups and summarizes repeated long failure reasons", async () => {
    vi.mocked(getRuns).mockResolvedValue([
      {
        id: 21,
        source_id: "nccl-arxiv-papers",
        status: "failed",
        finished_at: "2026-06-26 02:08:18",
        error: "The read operation timed out"
      },
      {
        id: 20,
        source_id: "nccl-arxiv-papers",
        status: "failed",
        finished_at: "2026-06-26 02:07:10",
        error:
          "Redirect response '301 Moved Permanently' for url 'http://export.arxiv.org/api/query?search_query=all:nccl&sortBy=submittedDate&sortOrder=descending&max_results=25'\nRedirect location: 'https://export.arxiv.org/api/query?search_query=all:nccl&sortBy=submittedDate&sortOrder=descending&max_results=25'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/301"
      },
      {
        id: 19,
        source_id: "nccl-huggingface-blog",
        status: "failed",
        finished_at: "2026-06-26 02:02:32",
        error: "timed out"
      },
      {
        id: 8,
        source_id: "nccl-github-releases",
        status: "failed",
        finished_at: "2026-06-26 01:57:04",
        error: "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1000)"
      }
    ]);

    render(<App />);

    expect((await screen.findAllByText("网络超时")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("2 次").length).toBeGreaterThan(0);
    expect(screen.getAllByText("HTTP 301 重定向").length).toBeGreaterThan(0);
    expect(screen.getAllByText("TLS/SSL 连接中断").length).toBeGreaterThan(0);
    expect(screen.queryByText(/export\.arxiv\.org\/api\/query/)).not.toBeInTheDocument();
    expect(screen.queryByText(/developer\.mozilla\.org/)).not.toBeInTheDocument();
  });

  it("shows wiki metrics and refreshes validation health on demand", async () => {
    vi.mocked(getWikiMetrics)
      .mockResolvedValueOnce(defaultWikiMetrics())
      .mockResolvedValueOnce({
        ...mockWikiMetrics,
        health: {
          ...mockWikiMetrics.health,
          latest_validation_at: "2026-06-26 03:00:00",
          summary: "轻量健康度：刚刚校验通过"
        }
      });

    render(<App />);

    expect(await screen.findByText("Wiki 监控")).toBeInTheDocument();
    expect(screen.getByText("3 页")).toBeInTheDocument();
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
    const storageCard = screen.getByLabelText("Wiki 占用空间明细");
    expect(within(storageCard).getByText("wiki")).toBeInTheDocument();
    expect(within(storageCard).getByText("1.0 KB")).toBeInTheDocument();
    expect(within(storageCard).getByText("raw")).toBeInTheDocument();
    expect(within(storageCard).getByText("768 B")).toBeInTheDocument();
    expect(within(storageCard).getByText("其他")).toBeInTheDocument();
    expect(within(storageCard).getByText("256 B")).toBeInTheDocument();
    expect(screen.getByText("100 分")).toBeInTheDocument();
    expect(screen.getByText(/最近校验：succeeded/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "刷新 wiki 校验" }));

    await waitFor(() => expect(validateWiki).toHaveBeenCalledWith(undefined));
    expect((await screen.findAllByText(/刚刚校验通过/)).length).toBeGreaterThan(0);
  });

  it("renders overview operational cards as concise info rows", async () => {
    vi.mocked(getSources).mockResolvedValue([
      {
        id: "nccl-arxiv-papers",
        name: "NCCL arXiv papers with a deliberately long display name for scanning",
        type: "arxiv",
        target_domain: "ai_infra",
        url: "http://export.arxiv.org/api/query?search_query=all:nccl",
        trust_level: "trusted",
        schedule: "weekly",
        run_policy: "scheduled",
        auto_ingest: true,
        auth_required: false,
        auth_state: "ready",
        topic: "NCCL arXiv papers",
        enabled: true
      },
      {
        id: "private-github-source",
        name: "Private GitHub issues",
        type: "github",
        target_domain: "ai_infra",
        url: "https://github.com/example/private/issues",
        trust_level: "trusted",
        schedule: "daily",
        run_policy: "scheduled",
        auto_ingest: true,
        auth_required: true,
        auth_state: "needs_auth_config",
        topic: "Private GitHub issues",
        enabled: true
      }
    ]);
    vi.mocked(getRuns).mockResolvedValue([
      {
        id: 31,
        source_id: "nccl-arxiv-papers",
        status: "succeeded",
        finished_at: "2026-06-26 03:15:00",
        fetched_count: 8,
        changed_count: 2,
        failed_count: 0
      }
    ]);

    render(<App />);

    await screen.findByText("NCCL arXiv papers with a deliberately long display name for scanning");
    expect(screen.getAllByText("每周").length).toBeGreaterThan(0);
    expect(screen.getAllByText("每日").length).toBeGreaterThan(0);
    expect(screen.getAllByText("arxiv · ai_infra").length).toBeGreaterThan(0);
    expect(screen.getAllByText("github · ai_infra").length).toBeGreaterThan(0);
    expect(screen.getByText("当前：needs_auth_config")).toBeInTheDocument();
    expect(screen.getByText("已抓 8，更新 2，失败 0")).toBeInTheDocument();
    expect(screen.getAllByText("成功").length).toBeGreaterThan(0);
    expect(screen.getAllByText("需认证配置").length).toBeGreaterThan(0);
    expect(screen.queryByText("nccl-arxiv-papers：succeeded")).not.toBeInTheDocument();
    expect(screen.queryByText("Private GitHub issues：needs_auth_config")).not.toBeInTheDocument();
  });

  it("shows latest source run state in the source subscription table", async () => {
    vi.mocked(getSources).mockResolvedValue([
      {
        id: "nccl-arxiv-papers",
        name: "NCCL arXiv papers",
        type: "arxiv",
        target_domain: "ai_infra",
        url: "http://export.arxiv.org/api/query?search_query=all:nccl",
        trust_level: "trusted",
        schedule: "weekly",
        run_policy: "scheduled",
        auto_ingest: true,
        auth_required: false,
        auth_state: "ready",
        topic: "NCCL arXiv papers",
        enabled: true,
        last_run_at: "2026-06-26 02:09:14",
        last_run_status: "succeeded"
      }
    ]);

    render(<App />);

    fireEvent.click(screen.getAllByText("来源订阅")[0]);

    await screen.findByText("NCCL arXiv papers");
    expect(screen.getByText("06/26 02:09")).toBeInTheDocument();
    expect(screen.getByText("succeeded")).toBeInTheDocument();
    expect(screen.queryByText("未运行")).not.toBeInTheDocument();
    expect(screen.queryByText("暂无状态")).not.toBeInTheDocument();
  });

  it("submits an ad hoc URL for automatic ingest and commit", async () => {
    render(<App />);

    fireEvent.click(screen.getAllByText("来源订阅")[0]);
    fireEvent.change(await screen.findByLabelText("入库 URL"), {
      target: { value: "https://example.com/doc?utm_source=x" }
    });
    fireEvent.click(screen.getByRole("button", { name: "抓取并入库" }));

    await waitFor(() =>
      expect(createManualIngest).toHaveBeenCalledWith({
        url: "https://example.com/doc?utm_source=x",
        domain: "ai_infra",
        auto_commit_enabled: true
      })
    );
    expect(await screen.findByText(/已入库并提交/)).toBeInTheDocument();
    expect(screen.getByText(/任务 #7/)).toBeInTheDocument();
    expect(screen.getByText(/abc1234/)).toBeInTheDocument();
  });

  it("shows a readable manual ingest baseline wait message", async () => {
    vi.mocked(createManualIngest).mockResolvedValue({
      status: "approved",
      reason: "waiting for clean git baseline before automatic retry",
      source_id: "manual-url-example-com-doc-9813a80c59",
      url: "https://example.com/doc",
      domain: "ai_infra",
      fetch: { fetch_run_id: 1, fetched_count: 1, changed_count: 1, skipped_count: 0 },
      task_id: 7,
      commit_sha: null
    });

    render(<App />);

    fireEvent.click(screen.getAllByText("来源订阅")[0]);
    fireEvent.change(await screen.findByLabelText("入库 URL"), {
      target: { value: "https://example.com/doc" }
    });
    fireEvent.click(screen.getByRole("button", { name: "抓取并入库" }));

    expect(await screen.findByText(/等待工作区清理后自动重试/)).toBeInTheDocument();
    expect(screen.getByText(/任务 #7/)).toBeInTheDocument();
    expect(screen.queryByText(/waiting for clean git baseline/)).not.toBeInTheDocument();
  });

  it("shows source run policy and accelerator discovery candidates", async () => {
    vi.mocked(getSources).mockResolvedValue([
      {
        id: "compute-accelerators-nvidia-h200",
        name: "NVIDIA H200 accelerator specs",
        type: "web",
        target_domain: "ai_infra",
        url: "https://www.nvidia.com/en-us/data-center/h200/",
        trust_level: "trusted",
        schedule: "monthly",
        run_policy: "once",
        auto_ingest: false,
        auth_required: false,
        auth_state: "ready",
        topic: "NVIDIA H200 accelerator specifications",
        enabled: true,
        last_run_status: "succeeded"
      }
    ]);
    vi.mocked(getAcceleratorCandidates).mockResolvedValue([
      {
        id: 7,
        vendor: "nvidia",
        model_name: "H300",
        normalized_model: "h300",
        scope: "gpu",
        source_profile_id: "compute-accelerator-discovery-nvidia-products",
        source_url: "https://www.nvidia.com/en-us/data-center/products/",
        evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
        evidence_text: "NVIDIA H300 GPU accelerator now available",
        confidence: 0.85,
        status: "pending",
        created_at: "2026-06-28 01:00:00",
        updated_at: "2026-06-28 01:00:00"
      }
    ]);

    render(<App />);

    fireEvent.click(screen.getAllByText("来源订阅")[0]);

    expect(await screen.findByText("新硬件候选")).toBeInTheDocument();
    expect(screen.getByText("H300")).toBeInTheDocument();
    expect(screen.getByText(/NVIDIA H300 GPU accelerator/)).toBeInTheDocument();
    expect(screen.getByText("一次性")).toBeInTheDocument();
  });

  it("renders accelerator discovery candidates in a readable review layout", async () => {
    const longEvidence =
      "Control to keep AI pipelines running at full speed. Learn More NVIDIA GB300 NVL72 connects 36 NVIDIA Grace CPUs and 72 NVIDIA Blackwell Ultra GPUs in a rack-scale design.";
    vi.mocked(getAcceleratorCandidates).mockResolvedValue([
      {
        id: 11,
        vendor: "nvidia",
        model_name: "GB300",
        normalized_model: "gb300",
        scope: "gpu",
        source_profile_id: "compute-accelerator-discovery-nvidia-products",
        source_url: "https://www.nvidia.com/en-us/data-center/products/",
        evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
        evidence_text: longEvidence,
        confidence: 0.9,
        status: "pending",
        created_at: "2026-06-28 01:00:00",
        updated_at: "2026-06-28 01:00:00"
      }
    ]);

    render(<App />);

    fireEvent.click(screen.getAllByText("来源订阅")[0]);

    const candidateTable = await screen.findByRole("table", { name: "新硬件候选" });
    const row = within(candidateTable).getByText("GB300").closest('[role="row"]');
    expect(row).toHaveClass("candidate-row");
    expect(within(row as HTMLElement).getByText(longEvidence)).toHaveClass("candidate-evidence-text");
    expect(within(row as HTMLElement).getByText(longEvidence)).toHaveAttribute("title", longEvidence);
    expect(within(row as HTMLElement).getByText("compute-accelerator-discovery-nvidia-products")).toHaveClass(
      "candidate-source-id"
    );
    expect(within(row as HTMLElement).getByText("https://www.nvidia.com/en-us/data-center/products/")).toHaveClass(
      "candidate-evidence-url"
    );
  });

  it("renders accelerator specs and refreshes after extraction backfill", async () => {
    vi.mocked(getAcceleratorSpecs)
      .mockResolvedValueOnce([mockAcceleratorSpec()])
      .mockResolvedValueOnce([
        {
          ...mockAcceleratorSpec(),
          resolved_specs: [
            ...mockAcceleratorSpec().resolved_specs,
            {
              field: "host_interface",
              value_text: "PCIe Gen5 x16",
              value_number: null,
              unit: "none",
              source_observation_id: 10,
              resolved_by: "rule",
              confidence: "0.9",
              conflict_status: "clean"
            }
          ]
        }
      ]);

    render(<App />);

    fireEvent.click(screen.getAllByText("参数库")[0]);

    expect(await screen.findByText("biren-166l")).toBeInTheDocument();
    expect(screen.getByText(/ai_asic/)).toBeInTheDocument();
    expect(screen.getByText("tdp")).toBeInTheDocument();
    expect(screen.getByText("600 W")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "https://www.birentech.com/product/hardware/166l/" })).toHaveAttribute(
      "href",
      "https://www.birentech.com/product/hardware/166l/"
    );
    expect(screen.queryByText(/compute-accelerators-biren-166l\/item\.md/)).not.toBeInTheDocument();
    expect(screen.queryByText("显存容量 256GB HBM3e")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "展开 biren-166l 观测证据" }));

    expect(screen.getByText("显存容量 256GB HBM3e")).toBeInTheDocument();
    expect(screen.getByText(/compute-accelerators-biren-166l\/item\.md/)).toBeInTheDocument();
    expect(screen.getByText(/compute-accelerators-biren-166l\/memory\.md/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "回填参数" }));

    await waitFor(() => expect(extractAcceleratorSpecs).toHaveBeenCalled());
    expect(await screen.findByText("host_interface")).toBeInTheDocument();
    expect(screen.getByText("已处理 1 个 SKU，1 条观测，1 个 resolved 字段")).toBeInTheDocument();
  });

  it("accepts and rejects accelerator discovery candidates", async () => {
    vi.mocked(getAcceleratorCandidates)
      .mockResolvedValueOnce([
        {
          id: 7,
          vendor: "nvidia",
          model_name: "H300",
          normalized_model: "h300",
          scope: "gpu",
          source_profile_id: "compute-accelerator-discovery-nvidia-products",
          source_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_text: "NVIDIA H300 GPU accelerator now available",
          confidence: 0.85,
          status: "pending",
          created_at: "2026-06-28 01:00:00",
          updated_at: "2026-06-28 01:00:00"
        }
      ])
      .mockResolvedValueOnce([]);

    render(<App />);

    fireEvent.click(screen.getAllByText("来源订阅")[0]);
    fireEvent.click(await screen.findByRole("button", { name: "接受 H300" }));

    await waitFor(() =>
      expect(acceptAcceleratorCandidate).toHaveBeenCalledWith(7, {
        source_id: "compute-accelerators-nvidia-h300",
        name: "nvidia H300 accelerator specs",
        url: "https://www.nvidia.com/en-us/data-center/products/",
        scope: ["gpu"],
        source_rank: "S1"
      })
    );

    vi.mocked(getAcceleratorCandidates)
      .mockResolvedValueOnce([
        {
          id: 8,
          vendor: "nvidia",
          model_name: "H301",
          normalized_model: "h301",
          scope: "gpu",
          source_profile_id: "compute-accelerator-discovery-nvidia-products",
          source_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_text: "NVIDIA H301 GPU accelerator",
          confidence: 0.75,
          status: "pending",
          created_at: "2026-06-28 01:00:00",
          updated_at: "2026-06-28 01:00:00"
        }
      ])
      .mockResolvedValueOnce([]);

    fireEvent.click(screen.getByRole("button", { name: "刷新来源" }));
    fireEvent.click(await screen.findByRole("button", { name: "拒绝 H301" }));

    await waitFor(() => expect(rejectAcceleratorCandidate).toHaveBeenCalledWith(8));
  });

  it("trusts the same base URL for accelerator discovery candidates", async () => {
    vi.mocked(getAcceleratorCandidates)
      .mockResolvedValueOnce([
        {
          id: 7,
          vendor: "nvidia",
          model_name: "GB300",
          normalized_model: "gb300",
          scope: "gpu",
          source_profile_id: "compute-accelerator-discovery-nvidia-products",
          source_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_text: "NVIDIA GB300 GPU accelerator",
          confidence: 0.9,
          status: "pending",
          created_at: "2026-06-28 01:00:00",
          updated_at: "2026-06-28 01:00:00"
        },
        {
          id: 8,
          vendor: "nvidia",
          model_name: "GB200",
          normalized_model: "gb200",
          scope: "gpu",
          source_profile_id: "compute-accelerator-discovery-nvidia-products",
          source_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_text: "NVIDIA GB200 GPU accelerator",
          confidence: 0.9,
          status: "pending",
          created_at: "2026-06-28 01:00:00",
          updated_at: "2026-06-28 01:00:00"
        },
        {
          id: 9,
          vendor: "example",
          model_name: "X900",
          normalized_model: "x900",
          scope: "gpu",
          source_profile_id: "compute-accelerator-discovery-example-products",
          source_url: "https://example.com/products/",
          evidence_url: "https://example.com/products/",
          evidence_text: "Example X900 GPU accelerator",
          confidence: 0.8,
          status: "pending",
          created_at: "2026-06-28 01:00:00",
          updated_at: "2026-06-28 01:00:00"
        }
      ])
      .mockResolvedValueOnce([
        {
          id: 9,
          vendor: "example",
          model_name: "X900",
          normalized_model: "x900",
          scope: "gpu",
          source_profile_id: "compute-accelerator-discovery-example-products",
          source_url: "https://example.com/products/",
          evidence_url: "https://example.com/products/",
          evidence_text: "Example X900 GPU accelerator",
          confidence: 0.8,
          status: "pending",
          created_at: "2026-06-28 01:00:00",
          updated_at: "2026-06-28 01:00:00"
        }
      ]);
    vi.mocked(trustAcceleratorCandidateSource).mockResolvedValueOnce({
      domain: "nvidia.com",
      accepted_count: 2,
      candidate_ids: [7, 8],
      accepted_source_ids: ["compute-accelerators-nvidia-gb300", "compute-accelerators-nvidia-gb200"],
      candidates: []
    });

    render(<App />);

    fireEvent.click(screen.getAllByText("来源订阅")[0]);
    fireEvent.click(await screen.findByRole("button", { name: "信任同站 GB300" }));

    await waitFor(() => expect(trustAcceleratorCandidateSource).toHaveBeenCalledWith(7));
    expect(await screen.findByText("已信任 nvidia.com，同站接受 2 个候选")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("GB300")).not.toBeInTheDocument());
    expect(screen.queryByText("GB200")).not.toBeInTheDocument();
    expect(screen.getByText("X900")).toBeInTheDocument();
  });

  it("manages domain channels, secrets, probes, and child sources", async () => {
    vi.mocked(getChannels)
      .mockResolvedValueOnce([
        {
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
        }
      ])
      .mockResolvedValueOnce([
        {
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
        },
        {
          id: "arxiv-org",
          target_domain: "ai_infra",
          name: "arXiv",
          base_url: "https://arxiv.org",
          base_url_normalized: "https://arxiv.org",
          probe_url: "https://arxiv.org",
          probe_method: "GET",
          probe_config_json: "{}",
          kind: "web",
          connector: "arxiv",
          trust_level: "trusted",
          enabled: true,
          auth_required: false,
          auth_mode: "none",
          auth_state: "ready",
          last_probe_status: null,
          last_probe_at: null,
          last_probe_summary: null,
          secret_configured: false,
          notes: "Public paper source",
          source_count: 0,
          created_at: "2026-07-03 10:00:00",
          updated_at: "2026-07-03 10:00:00"
        }
      ]);
    vi.mocked(getSourcesForChannel)
      .mockResolvedValueOnce([
        {
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
        }
      ])
      .mockResolvedValueOnce([
        {
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
        },
        {
          id: "nccl-github-releases",
          name: "NCCL GitHub releases",
          type: "github",
          fetcher_type: "github_releases",
          target_domain: "ai_infra",
          url: "https://github.com/NVIDIA/nccl/releases",
          channel_id: "github-com",
          channel_name: "GitHub",
          channel_base_url: "https://github.com",
          channel_auth_state: "ready",
          trust_level: "trusted",
          schedule: "weekly",
          run_policy: "scheduled",
          auto_ingest: true,
          auth_required: false,
          auth_state: "ready",
          topic: "NCCL releases",
          enabled: true
        }
      ]);
    vi.mocked(getChannelProbeRuns)
      .mockResolvedValueOnce([
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
      ])
      .mockResolvedValueOnce([
        {
          id: 8,
          channel_id: "github-com",
          status: "ready",
          started_at: "2026-07-03 10:05:00",
          finished_at: "2026-07-03 10:05:01",
          http_status: 200,
          final_url: "https://api.github.com/user",
          summary: "HTTP 200 from api.github.com",
          error: null
        },
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
      ]);

    render(<App />);

    fireEvent.click(screen.getAllByText("渠道管理")[0]);

    expect(await screen.findByRole("heading", { name: "Domain Channels" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("GitHub").length).toBeGreaterThan(0));
    expect(screen.getAllByText("https://github.com").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Selected notes")).toHaveValue("GitHub token verified");
    expect(screen.getByText("NCCL GitHub issues")).toBeInTheDocument();
    expect(screen.getAllByText("HTTP 200 from api.github.com").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Channel name"), { target: { value: "arXiv" } });
    fireEvent.change(screen.getByLabelText("Base URL"), { target: { value: "https://arxiv.org" } });
    fireEvent.change(screen.getByLabelText("Connector"), { target: { value: "arxiv" } });
    fireEvent.change(screen.getByLabelText("Channel notes"), { target: { value: "Public paper source" } });
    fireEvent.click(screen.getByRole("button", { name: "Add channel" }));

    await waitFor(() =>
      expect(createChannel).toHaveBeenCalledWith({
        target_domain: "ai_infra",
        name: "arXiv",
        base_url: "https://arxiv.org",
        probe_url: "",
        kind: "web",
        connector: "arxiv",
        trust_level: "trusted",
        enabled: true,
        auth_required: false,
        auth_mode: "none",
        notes: "Public paper source"
      })
    );

    fireEvent.click(await screen.findByRole("row", { name: "Select channel GitHub" }));
    fireEvent.change(screen.getByLabelText("Selected notes"), { target: { value: "GitHub token rotated" } });
    fireEvent.click(screen.getByRole("button", { name: "Save channel" }));
    await waitFor(() => expect(updateChannel).toHaveBeenCalledWith("github-com", { notes: "GitHub token rotated" }));

    fireEvent.change(screen.getByLabelText("Secret value"), { target: { value: "synthetic-secret-123" } });
    fireEvent.click(screen.getByRole("button", { name: "Replace secret" }));
    await waitFor(() =>
      expect(setChannelSecret).toHaveBeenCalledWith("github-com", {
        secret_kind: "synthetic_token",
        secret: "synthetic-secret-123"
      })
    );
    expect(screen.getByLabelText("Secret value")).toHaveValue("");
    expect(screen.queryByDisplayValue("synthetic-secret-123")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Verify access" }));
    await waitFor(() => expect(probeChannel).toHaveBeenCalledWith("github-com"));
    expect(await screen.findByText("Probe #8")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Source id"), { target: { value: "nccl-github-releases" } });
    fireEvent.change(screen.getByLabelText("Source name"), { target: { value: "NCCL GitHub releases" } });
    fireEvent.change(screen.getByLabelText("Source URL"), { target: { value: "https://github.com/NVIDIA/nccl/releases" } });
    fireEvent.change(screen.getByLabelText("Fetcher type"), { target: { value: "github_releases" } });
    fireEvent.change(screen.getByLabelText("Topic"), { target: { value: "NCCL releases" } });
    fireEvent.click(screen.getByRole("button", { name: "Add child source" }));

    await waitFor(() =>
      expect(createSource).toHaveBeenCalledWith({
        id: "nccl-github-releases",
        name: "NCCL GitHub releases",
        type: "github",
        fetcher_type: "github_releases",
        target_domain: "ai_infra",
        url: "https://github.com/NVIDIA/nccl/releases",
        channel_id: "github-com",
        trust_level: "trusted",
        schedule: "weekly",
        run_policy: "scheduled",
        auto_ingest: true,
        auth_required: false,
        topic: "NCCL releases",
        enabled: true
      })
    );
    expect(await screen.findByText("NCCL GitHub releases")).toBeInTheDocument();

    fireEvent.click(screen.getAllByText("来源订阅")[0]);
    expect(await screen.findByRole("heading", { name: "来源订阅" })).toBeInTheDocument();
    fireEvent.click(screen.getAllByText("入库队列")[0]);
    expect(await screen.findByRole("heading", { name: "入库队列" })).toBeInTheDocument();
  });

  it("keeps accepted candidates removed when post-accept refresh fails", async () => {
    vi.mocked(getAcceleratorCandidates)
      .mockResolvedValueOnce([
        {
          id: 7,
          vendor: "nvidia",
          model_name: "H300",
          normalized_model: "h300",
          scope: "gpu",
          source_profile_id: "compute-accelerator-discovery-nvidia-products",
          source_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_text: "NVIDIA H300 GPU accelerator now available",
          confidence: 0.85,
          status: "pending",
          created_at: "2026-06-28 01:00:00",
          updated_at: "2026-06-28 01:00:00"
        }
      ])
      .mockRejectedValueOnce(new Error("refresh failed"));

    render(<App />);

    fireEvent.click(screen.getAllByText("来源订阅")[0]);
    fireEvent.click(await screen.findByRole("button", { name: "接受 H300" }));

    await waitFor(() => expect(acceptAcceleratorCandidate).toHaveBeenCalledWith(7, expect.any(Object)));
    await waitFor(() => expect(screen.queryByText("H300")).not.toBeInTheDocument());
    expect(screen.getByText("候选已接受，刷新来源失败")).toBeInTheDocument();
    expect(screen.queryByText("接受候选失败")).not.toBeInTheDocument();
  });

  it("keeps rejected candidates removed when post-reject refresh fails", async () => {
    vi.mocked(getAcceleratorCandidates)
      .mockResolvedValueOnce([
        {
          id: 8,
          vendor: "nvidia",
          model_name: "H301",
          normalized_model: "h301",
          scope: "gpu",
          source_profile_id: "compute-accelerator-discovery-nvidia-products",
          source_url: "https://www.nvidia.com/en-us/data-center/products/",
          evidence_text: "NVIDIA H301 GPU accelerator",
          confidence: 0.75,
          status: "pending",
          created_at: "2026-06-28 01:00:00",
          updated_at: "2026-06-28 01:00:00"
        }
      ])
      .mockRejectedValueOnce(new Error("refresh failed"));

    render(<App />);

    fireEvent.click(screen.getAllByText("来源订阅")[0]);
    fireEvent.click(await screen.findByRole("button", { name: "拒绝 H301" }));

    await waitFor(() => expect(rejectAcceleratorCandidate).toHaveBeenCalledWith(8));
    await waitFor(() => expect(screen.queryByText("H301")).not.toBeInTheDocument());
    expect(screen.getByText("候选已拒绝，刷新来源失败")).toBeInTheDocument();
    expect(screen.queryByText("拒绝候选失败")).not.toBeInTheDocument();
  });

  it("shows pending queue item details with source link and raw preview", async () => {
    vi.mocked(getQueue).mockResolvedValue([
      {
        id: 42,
        source_id: "nccl-technical-blog",
        target_domain: "ai_infra",
        status: "pending",
        title: "NCCL Inspector",
        path: "personal-wiki/domains/ai_infra/raw/crawler/nccl-technical-blog/item.md",
        canonical_url: "https://developer.nvidia.com/blog/nccl-inspector/",
        raw_path: "personal-wiki/domains/ai_infra/raw/crawler/nccl-technical-blog/item.md",
        content_bytes: 1234,
        metadata: { published: "2026-06-26", article_fetch_method: "http" },
        content_preview: "This article explains NCCL Inspector and communication observability.",
        reason: "needs review"
      }
    ]);

    render(<App />);

    fireEvent.click(screen.getAllByText("入库队列")[0]);
    await screen.findByText("NCCL Inspector");
    expect(screen.getByText(/#42 · nccl-technical-blog · https:\/\/developer\.nvidia\.com\/blog\/nccl-inspector\//)).toBeInTheDocument();
    expect(screen.queryByText("personal-wiki/domains/ai_infra/raw/crawler/nccl-technical-blog/item.md")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看任务 42 详情" }));

    expect(screen.getByRole("link", { name: "https://developer.nvidia.com/blog/nccl-inspector/" })).toHaveAttribute(
      "href",
      "https://developer.nvidia.com/blog/nccl-inspector/"
    );
    expect(screen.getByText("personal-wiki/domains/ai_infra/raw/crawler/nccl-technical-blog/item.md")).toBeInTheDocument();
    expect(screen.getByText(/published/)).toBeInTheDocument();
    expect(screen.getByText(/NCCL Inspector and communication observability/)).toBeInTheDocument();
  });

  it("hides approved tasks from the manual pending queue list", async () => {
    vi.mocked(getQueue).mockResolvedValue([
      {
        id: 41,
        source_id: "nccl-arxiv-papers",
        status: "approved",
        title: "Approved paper"
      },
      {
        id: 42,
        source_id: "nccl-vllm-blog",
        status: "pending",
        title: "Pending article"
      }
    ]);

    render(<App />);

    fireEvent.click(screen.getAllByText("入库队列")[0]);
    await screen.findByText("Pending article");

    expect(screen.queryByText("Approved paper")).not.toBeInTheDocument();
    expect(screen.getByText("已通过待执行：1 条")).toBeInTheDocument();
  });

  it("marks a pending item site as a scheduled trusted source", async () => {
    vi.mocked(getQueue).mockResolvedValue([
      {
        id: 42,
        source_id: "nccl-vllm-blog",
        status: "pending",
        title: "Pending article",
        canonical_url: "https://vllm.ai/blog/nccl"
      }
    ]);
    vi.mocked(trustQueueSource).mockResolvedValueOnce({
      domain: "vllm.ai",
      approved_count: 1,
      schedule: "monthly"
    });

    render(<App />);

    fireEvent.click(screen.getAllByText("入库队列")[0]);
    await screen.findByText("Pending article");
    fireEvent.click(screen.getByRole("button", { name: "将任务 42 的网站设为信源" }));
    fireEvent.click(screen.getByLabelText("定期"));
    fireEvent.change(screen.getByLabelText("频率"), { target: { value: "monthly" } });
    fireEvent.click(screen.getByRole("button", { name: "确认设为信源" }));

    await waitFor(() =>
      expect(trustQueueSource).toHaveBeenCalledWith(42, { mode: "scheduled", frequency: "monthly" })
    );
    expect(await screen.findByText("已将 vllm.ai 设为信源，已通过 1 条同站点任务")).toBeInTheDocument();
  });
});
