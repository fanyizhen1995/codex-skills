import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the Chinese workbench shell with unauthenticated warning", () => {
    render(<App />);

    expect(screen.getByText("运维控制台")).toBeInTheDocument();
    expect(screen.getByText("知识工作台")).toBeInTheDocument();
    expect(screen.getByText("来源工作台")).toBeInTheDocument();
    expect(screen.getByText(/无登录/)).toBeInTheDocument();
  });
});
