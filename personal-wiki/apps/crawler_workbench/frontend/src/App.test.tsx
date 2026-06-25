import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./api", () => ({
  askCodex: vi.fn(),
  approveTask: vi.fn(),
  getDomains: vi.fn().mockResolvedValue([{ id: "ai_infra", name: "ai_infra" }]),
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
  rebuildSearch: vi.fn(),
  rejectTask: vi.fn(),
  runSource: vi.fn(),
  searchWiki: vi.fn()
}));

afterEach(() => {
  cleanup();
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
    await screen.findByText("暂无入库任务");
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
});
