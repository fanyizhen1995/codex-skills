import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the Chinese workbench shell with unauthenticated warning", () => {
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
  });
});
