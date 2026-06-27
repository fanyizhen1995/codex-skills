import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { AcceleratorCandidate } from "./types";
import {
  acceptAcceleratorCandidate,
  getAcceleratorCandidates,
  getQueue,
  getRuns,
  getSources,
  getWikiMetrics,
  rejectAcceleratorCandidate,
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
  getDomains: vi.fn().mockResolvedValue([{ id: "ai_infra", name: "ai_infra" }]),
  getAcceleratorCandidates: vi.fn().mockResolvedValue([]),
  getGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  getHealth: vi.fn().mockResolvedValue({
    status: "ok",
    bind_host: "0.0.0.0",
    bind_port: 8765,
    authenticated: false,
    warning: "无登录：仅可暴露在可信网络。后端可触发本机 Codex。"
  }),
  getJob: vi.fn(),
  getQueue: vi.fn().mockResolvedValue([]),
  getRuns: vi.fn().mockResolvedValue([]),
  getSources: vi.fn().mockResolvedValue([]),
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
  trustQueueSource: vi.fn().mockResolvedValue({ domain: "vllm.ai", approved_count: 1 }),
  validateWiki: vi.fn().mockResolvedValue({ status: "succeeded", stdout: "ok", stderr: "", validation_run_id: 7 })
}));

afterEach(() => {
  cleanup();
  vi.mocked(getAcceleratorCandidates).mockResolvedValue([]);
  vi.mocked(acceptAcceleratorCandidate).mockResolvedValue(mockAcceleratorCandidate("accepted"));
  vi.mocked(rejectAcceleratorCandidate).mockResolvedValue(mockAcceleratorCandidate("rejected"));
  vi.mocked(getQueue).mockResolvedValue([]);
  vi.mocked(getRuns).mockResolvedValue([]);
  vi.mocked(getSources).mockResolvedValue([]);
  vi.mocked(getWikiMetrics).mockResolvedValue(defaultWikiMetrics());
  vi.mocked(trustQueueSource).mockResolvedValue({ domain: "vllm.ai", approved_count: 1 });
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
    expect(screen.getAllByText("引用路径").length).toBeGreaterThan(0);
    expect(screen.getAllByText("知识关系图").length).toBeGreaterThan(0);
    expect(screen.getAllByText("主题时间线").length).toBeGreaterThan(0);
  });

  it("loads knowledge domains from the API instead of hard-coded defaults", async () => {
    render(<App />);

    fireEvent.click(screen.getAllByText("知识工作台")[0]);

    const selector = await screen.findByLabelText("Domain");
    await waitFor(() => expect(selector).toHaveValue("ai_infra"));

    expect(screen.getByRole("option", { name: "ai_infra" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "engineering" })).not.toBeInTheDocument();
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
