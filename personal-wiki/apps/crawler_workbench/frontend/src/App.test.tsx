import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./api", () => ({
  askCodex: vi.fn(),
  getDomains: vi.fn().mockResolvedValue([{ id: "ai_infra", name: "ai_infra" }]),
  getGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  getJob: vi.fn(),
  rebuildSearch: vi.fn(),
  searchWiki: vi.fn()
}));

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
});
